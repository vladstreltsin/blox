from blox.core.persist.base import Persister, PersisterError
from ...utils import join_not_none
from ...core._block import Port, _Block
from ...core.block import Sink
from torch.utils.tensorboard import SummaryWriter
from ...core.engine import Session
from enum import Enum


class SummaryType(Enum):
    SCALAR = 0,


class TensorBoardPersister(Persister):

    def __init__(self, name: str, block: _Block, save_enabled=True,
                 log_dir=None, *args, **kwargs):
        super(TensorBoardPersister, self).__init__(name=name, block=block, backend=None, final=False,
                                                   load_enabled=False, save_enabled=save_enabled)
        self._writer = SummaryWriter(log_dir=log_dir, *args, **kwargs)

    def can_save(self, obj, *args, **kwargs):
        return super(TensorBoardPersister, self).can_save(obj, *args, **kwargs) and isinstance(obj, Sink)

    def can_load(self, obj, *args, **kwargs):
        return False

    def __check_inputs(self, sink, session):
        if not isinstance(sink, Port):
            raise PersisterError(f"Incorrect type for Sink: {type(sink)} passed to {self}")

        if not isinstance(session, Session):
            raise PersisterError(f"Incorrect type for session: {type(session)} passed to {self}")

    def save(self, obj: Sink, session: Session = None, summary_type='scalar', tag=None, *args, **kwargs):
        value = obj.get(session)

        summary_type = SummaryType[summary_type.upper()]

        if summary_type is SummaryType.SCALAR:
            tag = join_not_none(self.block.separator, [self.get_obj_name(obj), tag])
            self._writer.add_scalar(tag=tag, scalar_value=value, *args, **kwargs)

        else:
            raise NotImplementedError

    def load(self, obj: Sink, *args, **kwargs):
        raise NotImplementedError
