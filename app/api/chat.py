from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
import json

router = APIRouter(prefix="/api", tags=["Chat & Négociation"])

class ConnectionManager:
    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: int):
        await websocket.accept()
        self.active.setdefault(conversation_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: int):
        if conversation_id in self.active:
            self.active[conversation_id].remove(websocket)

    async def broadcast(self, conversation_id: int, data: dict):
        for ws in self.active.get(conversation_id, []):
            await ws.send_json(data)

manager = ConnectionManager()


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: int,
    db: Session = Depends(get_db)
):
    await manager.connect(websocket, conversation_id)
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg = models.ChatMessage(
                conversation_id=conversation_id,
                sender_id=data["sender_id"],
                content=data["content"],
                message_type=data.get("type", "text"),
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            await manager.broadcast(conversation_id, {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "type": msg.message_type,
                "created_at": msg.created_at.isoformat(),
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)


@router.post("/conversations", response_model=schemas.ConversationOut, status_code=201)
def start_conversation(
    seller_id: int,
    product_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    existing = (
        db.query(models.ChatConversation)
        .filter(
            models.ChatConversation.buyer_id == current_user.id,
            models.ChatConversation.seller_id == seller_id,
            models.ChatConversation.product_id == product_id,
        )
        .first()
    )
    if existing:
        return existing

    conv = models.ChatConversation(
        buyer_id=current_user.id,
        seller_id=seller_id,
        product_id=product_id,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/conversations")
def my_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Conversations supprimées par cet utilisateur
    deleted_ids = [
        d.conversation_id for d in db.query(models.DeletedConversation)
        .filter(models.DeletedConversation.user_id == current_user.id).all()
    ]

    convs = (
        db.query(models.ChatConversation)
        .filter(
            (models.ChatConversation.buyer_id == current_user.id) |
            (models.ChatConversation.seller_id == current_user.id)
        )
        .all()
    )

    result = []
    for conv in convs:
        if conv.id in deleted_ids:
            continue
        buyer = db.query(models.User).filter(models.User.id == conv.buyer_id).first()
        seller = db.query(models.User).filter(models.User.id == conv.seller_id).first()
        product = db.query(models.Product).filter(models.Product.id == conv.product_id).first()
        result.append({
            "id": conv.id,
            "buyer_id": conv.buyer_id,
            "seller_id": conv.seller_id,
            "product_id": conv.product_id,
            "buyer_name": buyer.full_name if buyer else "Acheteur",
            "seller_name": seller.full_name if seller else "Vendeur",
            "product_name": product.name if product else "Produit",
        })
    return result


@router.get("/conversations/{conv_id}/messages")
def get_messages(
    conv_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.conversation_id == conv_id)
        .order_by(models.ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return messages


@router.post("/conversations/{conv_id}/messages")
def send_message(
    conv_id: int,
    data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    msg = models.ChatMessage(
        conversation_id=conv_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/negotiations", response_model=schemas.NegotiationOut, status_code=201)
def propose_price(
    data: schemas.NegotiationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    neg = models.Negotiation(
        conversation_id=data.conversation_id,
        proposed_price=data.proposed_price,
        quantity=data.quantity,
        proposed_by_id=current_user.id,
    )
    db.add(neg)
    msg = models.ChatMessage(
        conversation_id=data.conversation_id,
        sender_id=current_user.id,
        content=f"Proposition: {data.quantity} unité(s) à {data.proposed_price} FCFA",
        message_type="offer",
    )
    db.add(msg)
    db.commit()
    db.refresh(neg)
    return neg


@router.patch("/negotiations/{neg_id}/respond")
def respond_to_negotiation(
    neg_id: int,
    accepted: bool,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    neg = db.query(models.Negotiation).filter(models.Negotiation.id == neg_id).first()
    if not neg:
        raise HTTPException(404, "Négociation non trouvée")
    neg.status = models.NegotiationStatus.accepte if accepted else models.NegotiationStatus.refuse
    db.commit()
    return {"status": neg.status, "message": "Réponse enregistrée"}


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message non trouvé")
    if msg.sender_id != current_user.id:
        raise HTTPException(403, "Vous ne pouvez supprimer que vos propres messages")
    db.delete(msg)
    db.commit()
    return {"message": "Message supprimé"}


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    conv = db.query(models.ChatConversation).filter(
        models.ChatConversation.id == conv_id).first()
    if not conv:
        raise HTTPException(404, "Conversation non trouvée")
    if conv.buyer_id != current_user.id and conv.seller_id != current_user.id:
        raise HTTPException(403, "Accès refusé")

    # Vérifier si déjà supprimé
    existing = db.query(models.DeletedConversation).filter(
        models.DeletedConversation.conversation_id == conv_id,
        models.DeletedConversation.user_id == current_user.id
    ).first()

    if not existing:
        deleted = models.DeletedConversation(
            conversation_id=conv_id,
            user_id=current_user.id
        )
        db.add(deleted)
        db.commit()

    return {"message": "Conversation supprimée pour vous"}