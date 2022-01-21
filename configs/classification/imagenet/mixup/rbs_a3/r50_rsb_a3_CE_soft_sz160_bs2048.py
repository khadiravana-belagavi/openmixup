# Refers to `_RAND_INCREASING_TRANSFORMS` in pytorch-image-models
rand_increasing_policies = [
    dict(type='AutoContrast'),
    dict(type='Equalize'),
    dict(type='Invert'),
    dict(type='Rotate', magnitude_key='angle', magnitude_range=(0, 30)),
    dict(type='Posterize', magnitude_key='bits', magnitude_range=(4, 0)),
    dict(type='Solarize', magnitude_key='thr', magnitude_range=(256, 0)),
    dict(type='SolarizeAdd', magnitude_key='magnitude', magnitude_range=(0, 110)),
    dict(type='ColorTransform', magnitude_key='magnitude', magnitude_range=(0, 0.9)),
    dict(type='Contrast', magnitude_key='magnitude', magnitude_range=(0, 0.9)),
    dict(type='Brightness', magnitude_key='magnitude', magnitude_range=(0, 0.9)),
    dict(type='Sharpness', magnitude_key='magnitude', magnitude_range=(0, 0.9)),
    dict(type='Shear',
        magnitude_key='magnitude', magnitude_range=(0, 0.3), direction='horizontal'),
    dict(type='Shear',
        magnitude_key='magnitude', magnitude_range=(0, 0.3), direction='vertical'),
    dict(type='Translate',
        magnitude_key='magnitude', magnitude_range=(0, 0.45), direction='horizontal'),
    dict(type='Translate',
        magnitude_key='magnitude', magnitude_range=(0, 0.45), direction='vertical'),
]

_base_ = '../../../../base.py'
# model settings
model = dict(
    type='MixUpClassification',
    pretrained=None,
    alpha=0.1,  # str of list
    mix_mode="mixup",  # str or list, choose a mixup mode
    mix_args=dict(
        manifoldmix=dict(layer=(0, 3)),
        resizemix=dict(scope=(0.1, 0.8), use_alpha=True),
        fmix=dict(decay_power=3, size=(160,160), max_soft=0., reformulate=False)
    ),
    backbone=dict(
        # type='ResNet_mmcls',  # normal
        type='ResNet_Mix',  # required by 'manifoldmix'
        depth=50,
        num_stages=4,
        out_indices=(3,),  # no conv-1, x-1: stage-x
        norm_cfg=dict(type='SyncBN'),
        style='pytorch'),
    head=dict(
        type='ClsMixupHead',
        loss=dict(type='CrossEntropyLoss',  # mixup soft CE (one-hot encoding)
            use_soft=True, use_sigmoid=False, loss_weight=1.0),
        with_avg_pool=True, multi_label=True, two_hot=False,
        in_channels=2048, num_classes=1000)
)
# dataset settings
data_source_cfg = dict(type='ImageNet')
# ImageNet dataset
data_train_list = 'data/meta/ImageNet/train_labeled_full.txt'
data_train_root = 'data/ImageNet/train'
data_test_list = 'data/meta/ImageNet/val_labeled.txt'
data_test_root = 'data/ImageNet/val/'

dataset_type = 'ClassificationDataset'
img_norm_cfg = dict(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
train_pipeline = [
    dict(type='RandomResizedCrop', size=160, interpolation=3), # bicubic
    dict(type='RandomHorizontalFlip'),
    dict(type='RandAugment',
        policies=rand_increasing_policies,
        num_policies=2, total_level=10,
        magnitude_level=6, magnitude_std=0.5,
        hparams=dict(
            pad_val=[104, 116, 124], interpolation='bicubic')),
]
test_pipeline = [
    dict(type='Resize', size=236, interpolation=3),  # 0.95
    dict(type='CenterCrop', size=224),
    dict(type='ToTensor'),
    dict(type='Normalize', **img_norm_cfg),
]
# prefetch
prefetch = True
if not prefetch:
    train_pipeline.extend([dict(type='ToTensor'), dict(type='Normalize', **img_norm_cfg)])

data = dict(
    imgs_per_gpu=512,  # 512 x 4gpu = 2048
    workers_per_gpu=12,
    train=dict(
        type=dataset_type,
        data_source=dict(
            list_file=data_train_list, root=data_train_root,
            **data_source_cfg),
        pipeline=train_pipeline,
        prefetch=prefetch,
    ),
    val=dict(
        type=dataset_type,
        data_source=dict(
            list_file=data_test_list, root=data_test_root, **data_source_cfg),
        pipeline=test_pipeline,
        prefetch=False,
    ))
# additional hooks
custom_hooks = [
    dict(
        type='ValidateHook',
        dataset=data['val'],
        initial=False,
        interval=1,
        imgs_per_gpu=128,
        workers_per_gpu=4,
        eval_param=dict(topk=(1, 5)))
]
# optimizer
optimizer = dict(type='LAMB', lr=0.008, weight_decay=0.02,
                 paramwise_options={
                    '(bn|gn)(\d+)?.(weight|bias)': dict(weight_decay=0.),
                    'bias': dict(weight_decay=0.)})
optimizer_config = dict(grad_clip=None)

# lr scheduler
lr_config = dict(
    policy='CosineAnnealing',
    min_lr=1.0e-6,
    warmup='linear',
    warmup_iters=5, warmup_by_epoch=True,  # warmup 5 epochs.
    warmup_ratio=0.0001,
)
checkpoint_config = dict(interval=100)

# runtime settings
total_epochs = 100
