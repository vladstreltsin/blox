from blox_old.core.persistence.base import Persister, PersisterError
from blox_old.utils import join_not_none
from blox_old.core.block.base import Port
from blox_old.core.engine import Session, DefaultDevice


class PortPersister(Persister):

    def can_save(self, obj, *args, **kwargs):
        return super(PortPersister, self).can_save(obj, *args, **kwargs) and isinstance(obj, Port)

    def can_load(self, obj, *args, **kwargs):
        return super(PortPersister, self).can_load(obj, *args, **kwargs) and isinstance(obj, Port)

    def __check_inputs(self, port, session):
        if not isinstance(port, Port):
            raise PersisterError(f"Incorrect type for port: {type(port)} passed to {self}")

        if not isinstance(session, Session):
            raise PersisterError(f"Incorrect type for session: {type(session)} passed to {self}")

    def save(self, obj: Port, session: Session=None, tag=None, *args, **kwargs):
        self.__check_inputs(obj, session)
        port = obj

        if port not in session:
            raise PersisterError(f"Port {port} is not contained in the session {session}")

        # The value must be stored on the default device
        value = session[port].to(DefaultDevice()).value

        key = join_not_none(self.block.separator, [self.get_obj_name(port), tag])

        self.backend[key] = value

    def load(self, obj: Port, session: Session=None, tag=None, *args, **kwargs):
        self.__check_inputs(obj, session)
        port = obj
        key = join_not_none(self.block.separator, [self.get_obj_name(port), tag])
        if key not in self.backend:
            raise PersisterError(f"Key {key} is not contained in the backend {self.backend}")

        value = self.backend[key]
        session[port] = value
