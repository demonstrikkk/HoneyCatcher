import socketio
import logging

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

_rooms: dict[str, dict[str, str]] = {}


@sio.event
async def connect(sid, environ):
    logger.info("Socket.IO connect: %s", sid)


@sio.event
async def disconnect(sid):
    for room_id, members in list(_rooms.items()):
        if sid in members:
            role = members.pop(sid)
            await sio.leave_room(sid, room_id)
            await sio.emit("peer_disconnected", {"role": role}, room=room_id)
            if not members:
                del _rooms[room_id]
            break
    logger.info("Socket.IO disconnect: %s", sid)


@sio.event
async def join_room(sid, data):
    room_id = data.get("room_id")
    role    = data.get("role", "unknown")
    if not room_id:
        return

    await sio.enter_room(sid, room_id)
    _rooms.setdefault(room_id, {})[sid] = role

    await sio.emit("peer_joined", {"role": role}, room=room_id, skip_sid=sid)
    logger.info("Socket.IO %s joined room %s as %s", sid, room_id, role)


@sio.event
async def signal(sid, data):
    room_id = data.get("room_id")
    if room_id:
        await sio.emit("signal", data, room=room_id, skip_sid=sid)


@sio.event
async def leave_room(sid, data):
    room_id = data.get("room_id")
    if room_id and sid in _rooms.get(room_id, {}):
        role = _rooms[room_id].pop(sid)
        await sio.leave_room(sid, room_id)
        await sio.emit("peer_disconnected", {"role": role}, room=room_id)
