import detectron2.layers.roi_align_rotated as rar
from .....btorch.module import TorchModule


class ROIAlignRotated(TorchModule):
    def __init__(self, *args, name=None, **kwargs):
        super(ROIAlignRotated, self).__init__(module=rar.ROIAlignRotated(*args, **kwargs),
                                              In=('x', 'rois'), Out=1, name=name)
        self.lock_ports = True