_base_ = '../../../../base.py'
# model settings
model = dict(
    type='MixUpClassification',
    pretrained=None,
    alpha=1,
    mix_mode="mixup",
    mix_args=dict(
        manifoldmix=dict(layer=(0, 3)),
        resizemix=dict(scope=(0.1, 0.8), use_alpha=False),
        fmix=dict(decay_power=3, size=(32,32), max_soft=0., reformulate=False)
    ),
    backbone=dict(
        # type='ResNet_CIFAR',  # CIFAR version
        type='ResNet_Mix_CIFAR',  # required by 'manifoldmix'
        depth=18,
        num_stages=4,
        out_indices=(3,),  # no conv-1, x-1: stage-x
        style='pytorch'),
    head=dict(
        type='ClsMixupHead',  # soft CE decoupled mixup
        loss=dict(type='CrossEntropyLoss', loss_weight=1.0,
            use_soft=True, use_sigmoid=False, use_mix_decouple=True,  # decouple mixup CE
        ),
        with_avg_pool=True, multi_label=True, two_hot=False, two_hot_scale=1,  # not two-hot
        lam_scale_mode='pow', lam_thr=1, lam_idx=1,  # lam rescale, default as linear
        eta_weight=dict(eta=0.1, mode="both", thr=0.5),
        in_channels=512, num_classes=100)
)
# dataset settings
data_source_cfg = dict(type='CIFAR100', root='data/cifar100/')
dataset_type = 'ClassificationDataset'
img_norm_cfg = dict(mean=[0.4914, 0.4822, 0.4465], std=[0.2023, 0.1994, 0.201])
train_pipeline = [
    dict(type='RandomCrop', size=32, padding=4, padding_mode="reflect"),
    dict(type='RandomHorizontalFlip'),
]
test_pipeline = []
# prefetch
prefetch = True
if not prefetch:
    train_pipeline.extend([dict(type='ToTensor'), dict(type='Normalize', **img_norm_cfg)])
test_pipeline.extend([dict(type='ToTensor'), dict(type='Normalize', **img_norm_cfg)])

data = dict(
    imgs_per_gpu=100,
    workers_per_gpu=4,
    train=dict(
        type=dataset_type,
        data_source=dict(split='train', **data_source_cfg),
        pipeline=train_pipeline,
        prefetch=prefetch,
    ),
    val=dict(
        type=dataset_type,
        data_source=dict(split='test', **data_source_cfg),
        pipeline=test_pipeline,
        prefetch=False),
)

# additional hooks
custom_hooks = [
    dict(
        type='ValidateHook',
        dataset=data['val'],
        initial=False,
        interval=1,
        imgs_per_gpu=100,
        workers_per_gpu=4,
        eval_param=dict(topk=(1, 5)))
]

# optimizer
optimizer = dict(type='SGD', lr=0.1, momentum=0.9, weight_decay=0.0001)
optimizer_config = dict(grad_clip=None)

# learning policy
lr_config = dict(policy='CosineAnnealing', min_lr=0.)
checkpoint_config = dict(interval=800)

# runtime settings
total_epochs = 400
