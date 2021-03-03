import detectron2.layers.rotated_boxes as rb
from blox_old.core.block.base import AtomicFunction


class pairwise_iou_rotated(AtomicFunction):
    def __init__(self, *args, **kwargs):
        super(pairwise_iou_rotated, self).__init__(*args, **kwargs, In=('bx1', 'bx2'), Out=1)

    def fn(self, *args):
        return rb.pairwise_iou_rotated(*args)
