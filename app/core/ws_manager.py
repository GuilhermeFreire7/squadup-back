import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

from app.schemas.message import MessageRead

logger = logging.getLogger(__name__)


class ChatConnectionManager:
    """Mantém as conexões WebSocket ativas por partida, para broadcast de novas mensagens.

    Estado em memória de um único processo — suficiente para o volume esperado do MVP (mesmo
    racional do purge de refresh tokens no startup, ver `queue.md` "Lições da sessão 22"). Se o
    backend rodar em múltiplas réplicas simultâneas no futuro, um broker externo (ex.: Redis
    pub/sub) seria necessário para broadcast entre processos — fora do escopo desta fase.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, match_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[match_id].add(websocket)

    async def disconnect(self, match_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[match_id].discard(websocket)
            if not self._connections[match_id]:
                del self._connections[match_id]

    async def broadcast(self, match_id: str, message: MessageRead) -> None:
        """Envia `message` para todas as conexões ativas na partida.

        Nunca propaga exceção de uma conexão problemática — o mesmo racional de
        `notification_service.send_push` (D-Push-4): uma falha de entrega em um socket não
        pode derrubar o broadcast para os demais nem a chamada de quem originou a mensagem.
        Conexões que falharem ao receber são consideradas mortas e removidas.
        """
        connections = list(self._connections.get(match_id, ()))
        if not connections:
            return

        payload = message.model_dump(mode="json")
        stale: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                logger.warning("Conexão de chat morta na partida %s, removendo.", match_id)
                stale.append(connection)

        for connection in stale:
            await self.disconnect(match_id, connection)


manager = ChatConnectionManager()
