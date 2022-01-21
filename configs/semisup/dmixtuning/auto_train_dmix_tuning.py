import json
import os

from datetime import datetime
from mmcv import Config
from numpy.core.fromnumeric import prod, var
from functools import reduce
from operator import getitem
from itertools import product


class ConfigGenerator:
    def __init__(self, base_path: str, num_device: int) -> None:
        self.base_path = base_path
        self.num_device = num_device

    def _path_parser(self, path: str) -> str:
        assert isinstance(path, str)
        base_dir = os.path.join(*self.base_path.split('/')[:-1])
        base_name = self.base_path.split('/')[-1] # file name
        base_prefix = base_name.split('.')[0] # prefix
        backbone = base_prefix.split('_')[0]

        return base_dir, backbone, base_prefix

    def _combinations(self, var_dict: dict) -> list:
        assert isinstance(var_dict, dict)
        ls = list(var_dict.values())
        cbs = [x for x in product(*ls)] # all combiantions

        return cbs

    def set_nested_item(self, dataDict: dict, mapList: list, val) -> dict:
        """Set item in nested dictionary"""
        reduce(getitem, mapList[:-1], dataDict)[mapList[-1]] = val

        return dataDict

    def generate(self, model_var: dict, gm_var: dict, abbs: dict) -> None:
        assert isinstance(model_var, dict)
        assert isinstance(gm_var, dict)
        cfg = dict(Config.fromfile(self.base_path))
        base_dir, backbone, base_prefix = self._path_parser(self.base_path) # analysis path
        model_cbs = self._combinations(model_var)
        gm_cbs = self._combinations(gm_var)

        # params for global .sh file
        port = 99999
        time = datetime.today().strftime('%Y%m%d_%H%M%S')
        with open('{}_{}.sh'.format(os.path.join(base_dir, base_prefix), time), 'a') as shfile:
            # model setting
            for c in model_cbs:
                cfg_n = cfg # reset
                config_dir = os.path.join(base_dir, backbone)
                for i, kv in enumerate(zip(list(model_var.keys()), c)):
                    k = kv[0].split('.')
                    v = kv[1]
                    cfg_n = self.set_nested_item(cfg_n, k, v) # assign value
                    config_dir += '/{}{}'.format(str(k[-1]), str(v))
                comment = ' '.join(config_dir.split('/')[-i-1:]) # e.g. alpha1.0 mask_layer 1
                shfile.write('# {}\n'.format(comment))

                # base setting
                for b in gm_cbs:
                    base_params = ''
                    for kv in zip(list(gm_var.keys()), b):
                        a = kv[0].split('.')
                        n = kv[1]
                        cfg_n = self.set_nested_item(cfg_n, a, n)
                        base_params += '_{}{}'.format(str(a[-1]), str(n))

                    # saving json config
                    config_dir = config_dir.replace('.', '_')
                    base_params = base_params.replace('.', '_')
                    for word, abb in abbs.items():
                        base_params = base_params.replace(word, abb)
                    if not os.path.exists(config_dir):
                        os.makedirs(config_dir)
                    file_name = os.path.join(config_dir, '{}{}.json'.format(base_prefix, base_params))
                    with open(file_name, 'w') as configfile:
                        json.dump(cfg, configfile, indent=4)

                    # write cmds for .sh
                    port += 1
                    cmd = 'CUDA_VISIBLE_DEVICES=0 PORT={} bash tools/dist_train.sh {} {} &\nsleep 0.1s \n'.format(
                        port, file_name, self.num_device)
                    shfile.write(cmd)
                shfile.write('\n')
    print('Generation completed. Please modify the bash file to run experiments!')


def main():
    # per 50
    # base_path = "configs/semisup/mixtuning/cub200/r18_bce.py"
    base_path = "configs/semisup/mixtuning/cub200/r18_two_pow.py"
    
    abbs = {
        'total_epochs': 'ep',
        '(bn|gn)(\d+)?': 'bn',
    }
    # create nested dirs
    model_var = {
        'model.label_rescale': ['labeled', 'unlabeled'],
        # 'model.lam_bias': ['labeled', 'unlabeled'],
        'model.lam_bias': ['unlabeled'],
        # 'model.head_mix.two_hot': [True],
        # 'model.momentum': [0.999],
        # 'model.alpha': [2, 4, 8,],
        # 'optimizer.nesterov': [True, False],
    }
    gm_var = {
        # 'model.head_mix.two_hot_mode': ['pow'],
        # 'model.head_mix.two_hot_thr': [0.6, 0.8],
        'model.head_mix.two_hot_thr': [0.8],
        # 'model.head_mix.two_hot_idx': [0.5, 2],
        'model.head_mix.two_hot_idx': [0.5,],
        'model.mix_mode': ['mixup', 'cutmix', 'fmix', 'resizemix'],
        # 'model.mix_mode': ['cutmix',],
        # 'model.mix_mode': ['manifoldmix',],
        # 'model.mix_mode': ['saliencymix',],
        # 'model.mix_mode': ['fmix',],
        # 'model.mix_mode': ['resizemix',],
        'model.alpha': [0.2, 1],
        # 'optimizer.weight_decay': [5e-4,],
        'optimizer.paramwise_options.(bn|gn)(\d+)?.weight_decay': [5e-4, 0],
        # 'optimizer.nesterov': [False],
        # 'optimizer.nesterov': [True,],
        'total_epochs': [210]  # 50%
        # 'total_epochs': [130]  # 15%
        # 'total_epochs': [800]
    }
    
    num_device = 1
    
    generator = ConfigGenerator(base_path=base_path, num_device=num_device)
    generator.generate(model_var, gm_var, abbs)


if __name__ == '__main__':
    main()