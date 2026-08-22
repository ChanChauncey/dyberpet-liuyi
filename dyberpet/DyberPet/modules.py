import sys
from sys import platform
import time
import math
import uuid
import types
import random
import inspect
from typing import List
from datetime import datetime, timedelta

from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import interval, date, cron

from PySide6.QtCore import Qt, QTimer, QObject, QPoint
from PySide6.QtGui import QImage, QPixmap, QIcon, QCursor, QAction, QTransform
from PySide6.QtWidgets import *
from PySide6.QtCore import QObject, QThread, Signal

from DyberPet.utils import *
from DyberPet.conf import *


import DyberPet.settings as settings
basedir = settings.BASEDIR

# system config
sys_hp_tiers = settings.HP_TIERS #[0,50,80,100] #Line 48, 289
sys_nonDefault_prob = 0.35  # 固定值，不再按 tier 分档


##############################
#       Animation Module
##############################

class Animation_worker(QObject):
    sig_setimg_anim = Signal(name='sig_setimg_anim')
    sig_move_anim = Signal(float, float, name='sig_move_anim')
    sig_repaint_anim = Signal()
    acc_regist = Signal(dict, name='acc_regist')
    sig_start_sleep = Signal()

    def __init__(self, pet_conf, parent=None):
        """
        Animation Module
        Display user-defined animations randomly
        :param pet_conf: PetConfig class object in Main Widgets

        """
        super(Animation_worker, self).__init__(parent)
        self.pet_conf = pet_conf
        self.hp_cut_off = sys_hp_tiers #[0,50,80,100]
        self.current_status = [settings.pet_data.hp_tier,settings.pet_data.fv_lvl] #self._cal_status_type()
        self.nonDefault_prob = sys_nonDefault_prob
        self.act_cmlt_prob = self._cal_prob(self.current_status)
        self.is_killed = False
        self.is_paused = True  # 启动时暂停，由 startup_wake 结束后 resume
        self.current_act_name = None
        # 断点续播：记录被 pause 中断时的动作名与帧位置，resume 后从该帧继续，而不是从头播
        self._resume_act = None
        self._resume_frame = 0


    def run(self):
        """Run animation in a separate thread"""
        print('start running pet %s'%(self.pet_conf.petname))
        stand_repeat_prob = 0.7  # 连续待机后插播随机动作的概率
        stand_count = 0
        STAND_THRESHOLD = 3     # 连续播满这么多次待机后，才有机会插播随机动作
        # 完整待机动作：stand(0→240) = stand_idle(0-132) + stand_wag(133-240)
        # 过去 idle 只在 stand_idle(0-132) 空转、几乎到不了 wag(133-240)，
        # 这里统一播完整 stand，保证每次待机都"完整播到 240"（含尾巴摇）。
        full_stand = self.pet_conf.act_dict.get('stand') or self.pet_conf.default
        while not self.is_killed:
            while self.is_paused:
                time.sleep(0.2)
            if self.is_killed:
                break

            # 非待机动作（随机/交互残留）结束后，回到完整待机并连续播到 240
            if self.current_act_name is None or not self.current_act_name.startswith('stand'):
                self._run_acts([full_stand])
                stand_count = 0
            else:
                stand_count += 1
                if stand_count >= STAND_THRESHOLD and random.random() >= stand_repeat_prob:
                    # 攒够次数且未命中"继续待机"，插播一次随机动作（走路/喷嚏等）增加生动性
                    self.random_act()
                    stand_count = 0
                else:
                    self._run_acts([full_stand])
    
    def kill(self):
        self.is_paused = False
        self.is_killed = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def update_prob(self):
        self.current_status = [settings.pet_data.hp_tier,settings.pet_data.fv_lvl] #self._cal_status_type()
        self.act_cmlt_prob = self._cal_prob(self.current_status)

    def _cal_prob(self, current_status):
        act_conf = settings.act_data.allAct_params[settings.petname]
        act_name = [ k for k,v in act_conf.items() ]
        act_prob = [ act_conf[k]['act_prob'] for k in act_name ] #self.pet_conf.act_prob
        act_unlocked = [ act_conf[k]['unlocked'] for k in act_name ]
        act_inlist = [ act_conf[k]['in_playlist'] for k in act_name ]

        new_prob = []
        for i in range(len(act_name)):
            if not act_unlocked[i]:
                new_prob.append(0)
                continue

            # 只看 fv 解锁（unlocked 已由 _check_fvlock 判定），按 in_playlist 决定权重
            new_prob.append(act_prob[i] * int(act_inlist[i]))

        if sum(new_prob) != 0:
            new_prob = [i/sum(new_prob) for i in new_prob]
            #print(new_prob)
            total = 0
            act_cmlt_prob = []
            for i in range(len(new_prob)):
                total += new_prob[i]
                act_cmlt_prob.append(total)
            act_cmlt_prob[-1] = 1.0
        else:
            act_cmlt_prob = [0] * len(new_prob)

        act_cmlt_prob = [round(i,3) for i in act_cmlt_prob]
        #print(act_name)
        #print(act_cmlt_prob)
        return act_cmlt_prob

        

    def hpchange(self, hp_tier, direction):
        self.current_status[0] = int(hp_tier)
        self.act_cmlt_prob = self._cal_prob(self.current_status)
        #print('animation module is aware of the hp tier change!')

    def fvchange(self, fv_lvl):
        self.current_status[1] = int(fv_lvl)
        settings.act_data._pet_refreshed(fv_lvl)
        self.act_cmlt_prob = self._cal_prob(self.current_status)
        #print('animation module is aware of the fv lvl change! %i'%fv_lvl)

    

    def random_act(self) -> None:
        """
        随机执行动作
        :return:
        """
        # 如果正在睡觉，不执行随机动作
        if settings.is_sleeping:
            return

        acts = None
        accs = None
        # If HP type is not starving, this condition also makes sure only starving animation is played

        # If under focus timer, play focus animation
        if settings.focus_timer_on and self.pet_conf.focus:
            acts = [self.pet_conf.focus]

        # If there is only 1 animation, select the default animation mode
        elif set(self.act_cmlt_prob) == set([0,1]):
            act_idx = sum([i < 1.0 for i in self.act_cmlt_prob])
            act_name = list(settings.act_data.allAct_params[settings.petname].keys())[act_idx]
            acts, accs = self._get_acts(act_name)

        # Else random animation mode
        else:
            prob_num_0 = random.uniform(0, 1)
            # Random animation not selected, play default
            if prob_num_0 > self.nonDefault_prob:
                acts = [self.pet_conf.default]
            # Random animation selected
            else:
                prob_num = random.uniform(0, 1)
                act_idx = sum([ i < prob_num for i in self.act_cmlt_prob])
                # In some situation, no animation is selected (e.g., there is no random animation)
                if act_idx >= len(self.act_cmlt_prob):
                    acts = [self.pet_conf.default]
                else:
                    act_name = list(settings.act_data.allAct_params[settings.petname].keys())[act_idx]
                    acts, accs = self._get_acts(act_name)

        # 半屏方向限制：stand 状态触发行走时，左半屏只向右，右半屏只向左
        if acts:
            half = settings.screen_width / 2
            acts = [a for a in acts if not (
                a.direction == 'left' and settings.pet_center_x < half or
                a.direction == 'right' and settings.pet_center_x >= half
            )]
            if not acts:
                acts = [self.pet_conf.default]

        # 睡觉动画：交给 Interaction_worker 处理（onset→loop→wake 三段式）
        if acts and len(acts) > 0 and hasattr(acts[0], 'act_name') and acts[0].act_name == 'fallasleep_onset':
            self.is_paused = True
            self.sig_start_sleep.emit()
            return

        self._run_acts(acts, accs)

    
    def _get_acts(self, act_name):
        act_conf = settings.act_data.allAct_params[settings.petname][act_name]
        act_type = act_conf['act_type']
        if act_type == 'random_act':
            act_index = self.pet_conf.act_name.index(act_name)
            acts = self.pet_conf.random_act[act_index]
            accs = None
        
        elif act_type == 'accessory_act':
            acts = self.pet_conf.accessory_act[act_name]['act_list']
            accs = {'acc_list': self.pet_conf.accessory_act[act_name]['acc_list'],
                    'anchor': self.pet_conf.accessory_act[act_name]['anchor'],
                    'follow_main': self.pet_conf.accessory_act[act_name].get('follow_main', False),
                    'speed_follow_main': self.pet_conf.accessory_act[act_name].get('speed_follow_main', 5),
                    'follow_mouse': self.pet_conf.accessory_act[act_name].get('follow_mouse', False)}
        elif act_type == 'customized':
            acts = self.pet_conf.custom_act[act_name]['act_list']
            if self.pet_conf.custom_act[act_name]['acc_list']:
                accs = {'acc_list': self.pet_conf.custom_act[act_name]['acc_list'],
                        'anchor': self.pet_conf.custom_act[act_name]['anchor'],
                        'name': 'customized_acc' # For Accessory module to judge the type
                        }
            else:
                accs = None
        else:
            acts = None
            accs = None

        return acts, accs


    def _run_acts(self, acts: List[Act], accs: List[Act] = None) -> None:
        """
        执行动画, 将一个动作相关的图片循环展示
        :param acts: 一组关联动作
        :return:
        """
        #start = time.time()
        if accs:
            self.acc_regist.emit(accs)
        for act in acts:
            self._run_act(act)
        #print('%.2fs'%(time.time()-start))
        #self.is_run_act = False

    def _run_act(self, act: Act) -> None:
        """
        加载图片执行移动
        :param act: 动作
        :return:
        """
        # 设置当前动画名称
        self.current_act_name = act.act_name if hasattr(act, 'act_name') else None

        # 断点续播：若被 pause 中断的是同一个动作，从断点帧继续；否则从头播
        if self._resume_act == self.current_act_name and not isinstance(act, list):
            start_frame = self._resume_frame
        else:
            start_frame = 0
        self._resume_act = None
        self._resume_frame = 0

        # if this is a skipping act
        if isinstance(act, list):
            for i in range(act[1]):
                if self.is_paused:
                    break
                if self.is_killed:
                    break
                time.sleep(act[0]/1000)
            return

        for i in range(act.act_num):

            #while self.is_paused:
            #    time.sleep(0.2)
            if self.is_paused:
                break
            if self.is_killed:
                break

            imgs = act.images
            for frame_idx in range(start_frame, len(imgs)):

                #while self.is_paused:
                #    time.sleep(0.2)
                if self.is_paused:
                    # 记录断点，下次 resume 从该帧继续，而不是从头播
                    self._resume_act = self.current_act_name
                    self._resume_frame = frame_idx
                    break
                if self.is_killed:
                    break

                #global current_img, previous_img
                settings.previous_img = settings.current_img
                settings.current_img = imgs[frame_idx]
                settings.previous_anchor = settings.current_anchor
                settings.current_anchor =  [int(j * settings.tunable_scale) for j in act.anchor]
                #print('anim', settings.previous_anchor, settings.current_anchor)
                self.sig_setimg_anim.emit()
                #time.sleep(act.frame_refresh) ######## sleep 和 move 是不是应该反过来？
                #if act.need_move:
                self._move(act, frame_idx)
                time.sleep(act.frame_refresh)
                #else:
                #    self._static_act(self.pos())
                self.sig_repaint_anim.emit()

            if self.is_paused:
                break
            start_frame = 0  # 当前 act_num 迭代播完，下一轮从头
    '''
    def _static_act(self, pos: QPoint) -> None:
        """
        静态动作判断位置 - 目前舍弃不用
        :param pos: 位置
        :return:
        """
        screen_geo = QDesktopWidget().screenGeometry()
        screen_width = screen_geo.width()
        screen_height = screen_geo.height()
        border = self.pet_conf.size
        new_x = pos.x()
        new_y = pos.y()
        if pos.x() < border:
            new_x = screen_width - border
        elif pos.x() > screen_width - border:
            new_x = border
        if pos.y() < border:
            new_y = screen_height - border
        elif pos.y() > screen_height - border:
            new_y = border
        self.move(new_x, new_y)
    '''

    def _get_frame_speed(self, act, frame_idx):
        """根据当前帧索引返回该帧的移动速度"""
        if not act.move_phases:
            return act.frame_move
        for phase in act.move_phases:
            if phase['start'] <= frame_idx <= phase['end']:
                speed = phase['speed']
                if isinstance(speed, (int, float)):
                    return speed
                parts = speed.split('->')
                s0, s1 = float(parts[0]), float(parts[1])
                if phase['end'] == phase['start']:
                    return s1
                t = (frame_idx - phase['start']) / (phase['end'] - phase['start'])
                return s0 + t * (s1 - s0)
        return 0.0

    def _move(self, act: QAction, frame_idx=0) -> None:
        """
        移动动作
        :param act: 动作
        :param frame_idx: 当前帧索引
        :return
        """
        plus_x = 0.
        plus_y = 0.
        direction = act.direction
        speed = self._get_frame_speed(act, frame_idx)
        if direction is None:
            pass
        else:
            if direction == 'right':
                plus_x = speed

            if direction == 'left':
                plus_x = -speed

            if direction == 'up':
                plus_y = -speed

            if direction == 'down':
                plus_y = speed
        if plus_x == 0 and plus_y == 0:
            pass
        else:
            self.sig_move_anim.emit(plus_x, plus_y)




##############################
#      Interaction Module
##############################

class Interaction_worker(QObject):

    sig_setimg_inter = Signal(name='sig_setimg_inter')
    sig_move_inter = Signal(float, float, name='sig_move_inter')
    sig_bounce_move = Signal(float, float, name='sig_bounce_move')
    #sig_repaint_inter = Signal()
    sig_act_finished = Signal()
    sig_interact_note = Signal(str, str, name='sig_interact_note')

    acc_regist = Signal(dict, name='acc_regist')
    query_position = Signal(str, name='query_position')
    stop_trackMouse = Signal(name='stop_trackMouse')

    def __init__(self, pet_conf, parent=None):
        """
        Interaction Module
        Respond immediately to signals and run functions defined
        
        pet_conf: PetConfig class object in Main Widgets

        """
        super(Interaction_worker, self).__init__(parent)
        self.pet_conf = pet_conf
        self.is_killed = False
        self.is_paused = False
        self.interact = None
        self.act_name = None # everytime making act_name to None, don't forget to set settings.playid to 0
        self.interact_altered = False
        self.hptier = sys_hp_tiers #[0, 50, 80, 100]
        self.pat_idx = None

        self.timer = QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.run)
        #print(self.pet_conf.interact_speed)
        self.timer.start(self.pet_conf.interact_speed)
        #self.start = time.time()


    def run(self):
        #print(time.time()-self.start)
        #self.start = time.time()
        #print('start_run')
        if self.interact is None:
            return
        elif self.interact not in dir(self):
            self.interact = None
        else:
            if self.interact_altered:
                self.empty_interact()
                self.interact_altered = False
            getattr(self,self.interact)(self.act_name)

    def _get_animation_type(self, act_name):
        act_conf = settings.act_data.allAct_params[settings.petname]
        if act_name not in act_conf:
            return None
        act_type = act_conf[act_name]['act_type']
        if act_type == 'random_act':
            return 'animat'
    
        elif act_type == 'accessory_act':
            return 'anim_acc'
        
        elif act_type == 'customized':
            return 'customized'

    def start_interact(self, interact, act_name=None):
        # If Act selected from menu/panel, judge animation type first
        if interact == "actlist":
            interact = self._get_animation_type(act_name)
            if not interact:
                self.stop_interact()
                return
            #elif interact == 'customized':
            #    print("Not implemented")
            #    self.stop_interact()
            #    return

        sound_list = []
        if interact == 'animat' and act_name in self.pet_conf.act_name:
            sound_list = self.pet_conf.act_sound[self.pet_conf.act_name.index(act_name)]
            hp_lvl = 0  # tier 系统已移除，不再检查饱食度门槛

        elif interact == 'anim_acc' and act_name in self.pet_conf.acc_name:
            sound_list = self.pet_conf.accessory_act[act_name]['sound']
            hp_lvl = self.pet_conf.accessory_act[act_name]['act_type'][0]
        
        # Customized animation currently doesn't have sound

        if len(sound_list) > 0 and settings.pet_data.hp_tier >= hp_lvl:
            sound_name = random.choice(sound_list)
            self.sig_interact_note.emit(sound_name, '')

        self.interact_altered = True
        if interact == 'anim_acc' or interact == 'customized':
            self.first_acc = True

        if self.interact == 'followTarget':
            if self.act_name == 'mouse':
                self.stop_trackMouse.emit()

        # 睡觉动画
        if interact == 'sleep':
            interact = 'sleeping'  # 映射到实际方法名
            settings.is_sleeping = True

        # 启动阶段醒来动画
        if interact == 'startup_wake':
            interact = 'startup_wake'
            settings.is_starting_up = True
            import os as _os
            if _os.environ.get('DYBERPET_TEST_WAKE_PROBE'):
                print('[WAKE_PROBE] start_interact startup_wake -> is_starting_up=True')

        # sample pat animation
        if interact == 'patpat':
            self.pat_idx = self.sample_pat_anim()
        self.interact = interact
        self.act_name = act_name
        # 切换动画时重置播放状态
        settings.playid = 0
        settings.act_id = 0
        pass
    
    def kill(self):
        self.is_paused = False
        self.is_killed = True
        #self.timer.stop()
        # terminate thread

    def pause(self):
        self.is_paused = True
        #self.timer.stop()

    def resume(self):
        self.is_paused = False

    def stop_interact(self):
        self.interact = None
        self.act_name = None
        self.first_acc = False
        settings.playid = 0
        settings.act_id = 0
        settings.is_sleeping = False
        settings.is_starting_up = False
        self.sig_act_finished.emit()

    def empty_interact(self):
        settings.playid = 0
        settings.act_id = 0

    def sample_pat_anim(self):
        hp_tier = settings.pet_data.hp_tier
        prob = [1*(0.25**(abs(i-hp_tier))) for i in range(len(settings.HP_TIERS))]
        prob = [i/sum(prob) for i in prob]
        act_idx = random.choices([i for i in range(len(settings.HP_TIERS))], weights=prob, k=1)[0]
        return act_idx

    def img_from_act(self, act):

        if settings.current_act != act:
            settings.previous_act = settings.current_act
            settings.current_act = act
            settings.playid = 0

        # if this is a skipping act
        if isinstance(act, list):
            n_repeat = math.ceil(act[0]/self.pet_conf.interact_speed) * act[1]
            settings.playid += 1
            if settings.playid >= n_repeat:
                settings.playid = 0
        else:
            n_repeat = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
            img_list_expand = [item for item in act.images for i in range(n_repeat)] * act.act_num

            # 动画已结束，不再递增 playid
            if settings.playid >= len(img_list_expand):
                return

            # 弹跳动画不循环：clamp 到最后一帧，等待切换到 land_stay
            if settings.bouncing and settings.playid >= len(img_list_expand):
                settings.playid = len(img_list_expand) - 1

            img = img_list_expand[settings.playid]

            settings.playid += 1
            if settings.playid >= len(img_list_expand):
                if settings.bouncing:
                    settings.playid = len(img_list_expand) - 1  # 停在最后一帧
                else:
                    settings.playid = len(img_list_expand)  # 保持在终点，由调用方重置
            settings.previous_img = settings.current_img
            settings.current_img = img
            settings.previous_anchor = settings.current_anchor
            settings.current_anchor = [int(i * settings.tunable_scale) for i in act.anchor]

    def animat(self, act_name):
        try:
            self._animat_inner(act_name)
        except Exception as e:
            import traceback
            print(f"[animat EXCEPTION] {e}")
            traceback.print_exc()
            self.stop_interact()

    def _animat_inner(self, act_name):
        # 如果正在睡觉，调用 sleeping 方法处理睡觉动画
        if settings.is_sleeping:
            self.sleeping(act_name)
            return

        # 启动阶段，锁定为 startup_wake 动画
        if settings.is_starting_up:
            self.startup_wake(act_name)
            return

        # 首先检查是否是交互动作（land_bounce, land_stay 等）
        if act_name in self.pet_conf.act_dict:
            act = self.pet_conf.act_dict[act_name]
            # 创建临时的 acts 列表
            acts = [act]
            act_id = settings.act_id
        else:
            # 查找随机动作
            try:
                acts_index = self.pet_conf.act_name.index(act_name)
            except ValueError:
                acts_index = None
                for i, name in enumerate(self.pet_conf.act_name):
                    act_list = self.pet_conf.random_act[i]
                    if hasattr(act_list, '__iter__') and len(act_list) > 0:
                        if hasattr(act_list[0], 'act_name') and act_list[0].act_name == act_name:
                            acts_index = i
                            break
                if acts_index is None:
                    print(f"[animat] act_name='{act_name}' NOT FOUND, stopping")
                    self.stop_interact()
                    return

            acts = self.pet_conf.random_act[acts_index]
            act_id = settings.act_id

        if act_id >= len(acts):
            self.stop_interact()
        else:
            act = acts[act_id]
            n_repeat = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
            n_repeat *= len(act.images) * act.act_num

            # land_bounce：弹跳物理+精灵图由 Interaction 线程驱动
            if act_name == 'land_bounce' and settings.bouncing:
                settings.bounce_tick += 1
                ticks_per_frame = max(math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000)), 1)
                if settings.bounce_tick == 1:
                    pass
                n = settings.bounce_total_frames
                pf = settings.bounce_tick // ticks_per_frame
                pf_prev = (settings.bounce_tick - 1) // ticks_per_frame
                # 窗口位置：每次 tick 都更新
                # 弹跳只在前半段完成（约 0-15 帧），避免 land_15 双脚已站直后窗口还在往下掉。
                # 后半段窗口保持贴地，让落地/站立动画自然播放。
                progress = min(settings.bounce_tick / max((n - 1) * ticks_per_frame, 1), 1.0)
                phase = min(progress / 0.5, 1.0)
                t = (phase - 0.5) / 0.5
                cur_offset_y = -settings.bounce_peak_height * (1.0 - t * t)
                cur_offset_x = settings.bounce_drift_x * progress
                dx = cur_offset_x - settings.bounce_prev_offset_x
                dy = cur_offset_y - settings.bounce_prev_offset_y
                settings.bounce_prev_offset_x = cur_offset_x
                settings.bounce_prev_offset_y = cur_offset_y
                self.sig_bounce_move.emit(dx, dy)
                # 精灵图切换（首帧或帧变化时）— 直接取帧，不走 img_from_act
                if pf > pf_prev or settings.bounce_tick == 1:
                    frame_idx = min(pf, len(act.images) - 1)
                    settings.previous_img = settings.current_img
                    settings.current_img = act.images[frame_idx]
                    settings.previous_anchor = settings.current_anchor
                    settings.current_anchor = [int(i * settings.tunable_scale) for i in act.anchor]
                    self.sig_setimg_inter.emit()
                # bounce 播满 n 帧后结束（与原视频时长一致）
                if pf >= n:
                    settings.bouncing = False
                    settings.act_id = 0
                    settings.playid = 0
                    self.start_interact('animat', 'land_stay')
                    return
                return

            self.img_from_act(act)

            if act_name == 'land_stay':
                frame_idx = settings.playid % len(act.images) if len(act.images) > 0 else 0

            if settings.playid >= n_repeat-1:
                settings.act_id += 1
                settings.playid = 0

                # land_bounce：sprite 循环重置
                if act_name == 'land_bounce' and settings.bouncing:
                    settings.act_id = 0

                # land_stay：播放完成后停止
                if act_name == 'land_stay':
                    self.stop_interact()
                    return

            if act_name == 'onfloor' and settings.fall_right:
                settings.previous_img = settings.current_img
                transform = QTransform()
                transform.scale(-1, 1)
                settings.current_img = settings.current_img.transformed(transform) #.mirrored(True, False)
                settings.current_anchor = [int(i * settings.tunable_scale) for i in act.anchor]
                settings.current_anchor = [-settings.current_anchor[0], settings.current_anchor[1]]

            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()
                n_repeat_per_frame = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
                frame_idx = (settings.playid // n_repeat_per_frame) % len(act.images) if act.images else 0
                self._move(act, frame_idx)
        #print('%.5fs'%(time.time()-start))
        
    def anim_acc(self, acc_name):

        # 判断是否满足动作饱食度要求
        if settings.pet_data.hp_tier < self.pet_conf.accessory_act[acc_name]['act_type'][0]:
            message = f"[{acc_name}]" + " " + self.tr("needs Satiety be larger than") + f" {self.hptier[self.pet_conf.accessory_act[acc_name]['act_type'][0]-1]}"
            self.sig_interact_note.emit('status_hp', message) #'[%s] 需要饱食度%i以上哦'%(acc_name, self.hptier[self.pet_conf.accessory_act[acc_name]['act_type'][0]-1]))
            self.stop_interact()
            return

        if self.first_acc:
            accs = self.pet_conf.accessory_act[acc_name]
            self.acc_regist.emit(accs)
            self.first_acc = False

        acts = self.pet_conf.accessory_act[acc_name]['act_list']

        if settings.act_id >= len(acts):
            #settings.act_id = 0
            #self.interact = None
            self.stop_interact()
            #self.sig_act_finished.emit()
        else:
            act = acts[settings.act_id]
            n_repeat = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
            n_repeat *= len(act.images) * act.act_num
            self.img_from_act(act)
            if settings.playid >= n_repeat-1:
                settings.act_id += 1
                settings.playid = 0

            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()
                self._move(act)

    def customized(self, act_name):

        # 判断是否满足动作饱食度要求
        if settings.pet_data.hp_tier < self.pet_conf.custom_act[act_name]['act_type'][0]:
            message = f"[{act_name}]" + " " + self.tr("needs Satiety be larger than") + f" {self.hptier[self.pet_conf.custom_act[act_name]['act_type'][0]-1]}"
            self.sig_interact_note.emit('status_hp', message)
            self.stop_interact()
            return

        if self.first_acc:
            if self.pet_conf.custom_act[act_name]['acc_list']:
                accs = {'acc_list': self.pet_conf.custom_act[act_name]['acc_list'],
                        'anchor': self.pet_conf.custom_act[act_name]['anchor'],
                        'name': 'customized_acc' # For Accessory module to judge the type
                        }
                self.acc_regist.emit(accs)
            self.first_acc = False

        acts = self.pet_conf.custom_act[act_name]['act_list']

        if settings.act_id >= len(acts):
            #settings.act_id = 0
            #self.interact = None
            self.stop_interact()
            #self.sig_act_finished.emit()
        else:
            act = acts[settings.act_id]
            # if this is a skipping act
            if isinstance(act, list):
                n_repeat = math.ceil(act[0]/self.pet_conf.interact_speed) * act[1]
            else:
                n_repeat = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
                n_repeat *= len(act.images) * act.act_num
            self.img_from_act(act)
            if settings.playid >= n_repeat-1:
                settings.act_id += 1
                settings.playid = 0

            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()
                self._move(act)

    def patpat(self, act_name):
        acts = [self.pet_conf.patpat[self.pat_idx]]
        #print(settings.act_id, len(acts))
        if settings.act_id >= len(acts):
            #settings.act_id = 0
            #self.interact = None
            self.stop_interact()
            #self.sig_act_finished.emit()
        else:
            act = acts[settings.act_id]
            n_repeat = math.ceil(act.frame_refresh / (self.pet_conf.interact_speed / 1000))
            n_repeat *= len(act.images) * act.act_num
            self.img_from_act(act)
            if settings.playid >= n_repeat-1:
                settings.act_id += 1
                settings.playid = 0

            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()
                self._move(act)

    def mousedrag(self, act_name):

        # Falling is OFF
        if not settings.set_fall:
            if settings.draging==1:
                acts = self.pet_conf.drag

                self.img_from_act(acts)
                if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                    self.sig_setimg_inter.emit()

            else:
                self.stop_interact()
                #self.interact = None
                #self.act_name = None
                #settings.playid = 0

        # Falling is ON
        elif settings.set_fall==1 and settings.onfloor==0:
            if settings.draging==1:
                # 首次按下：播放 drag_start，播完后切到 grab_loop
                if not settings.drag_start_done:
                    acts = self.pet_conf.drag_start
                    n_repeat = math.ceil(acts.frame_refresh / (self.pet_conf.interact_speed / 1000))
                    n_repeat *= len(acts.images) * acts.act_num
                    self.img_from_act(acts)
                    pass
                    if settings.playid >= n_repeat - 1:
                        settings.drag_start_done = True
                        settings.playid = 0
                        pass
                else:
                    # drag_start 播完，循环播放 grab_loop
                    acts = self.pet_conf.drag
                    prev_playid = settings.playid
                    self.img_from_act(acts)
                    # 循环：playid 不再增长说明动画到头，重置从头播
                    if settings.playid == prev_playid:
                        settings.playid = 0

                if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                    self.sig_setimg_inter.emit()

            elif settings.draging==0:
                # fall 动画：分阶段播放
                # 阶段1: fall (18-192) 播放一次，前半段慢速后半段加速
                # 阶段2: fall_loop (123→192) 正放循环直到触地
                if not hasattr(self, '_fall_logged'):
                    self._fall_logged = True
                    pass

                # 基础 tick 数（×0.5 = 2倍速）
                normal_ticks = math.ceil(0.02 / (self.pet_conf.interact_speed / 1000) / 0.7 * 0.5)

                # 帧 18-43 使用 2 倍速（tick 数减半）
                fast_ticks = max(normal_ticks // 2, 1)

                # 根据当前帧选择速度
                if settings.fall_phase == 'fall' and 18 <= settings.fall_frame <= 43:
                    base_ticks = fast_ticks
                else:
                    base_ticks = normal_ticks

                settings.fall_tick += 1
                if settings.fall_tick >= base_ticks:
                    settings.fall_tick = 0

                    if settings.fall_phase == 'fall':
                        # 阶段1: fall 播放 18-192，只播放一次
                        settings.fall_frame += 1
                        if settings.fall_frame >= 192:
                            settings.fall_frame = 192  # 停在最后一帧

                # 设置当前帧图片
                settings.previous_img = settings.current_img
                settings.previous_anchor = settings.current_anchor

                if settings.fall_phase == 'fall':
                    acts = self.pet_conf.fall
                    frame_idx = min(settings.fall_frame - acts.frame_start, len(acts.images) - 1)
                    settings.current_img = acts.images[max(frame_idx, 0)]
                    settings.current_anchor = [int(i * settings.tunable_scale) for i in acts.anchor]

                if settings.fall_right:
                    transform = QTransform()
                    transform.scale(-1, 1)
                    settings.current_img = settings.current_img.transformed(transform)
                    settings.current_anchor = [-settings.current_anchor[0], settings.current_anchor[1]]

                if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                    self.sig_setimg_inter.emit()

                self.drop()

        else:
            # 触地后不再由 mousedrag 处理，弹跳由 _move_customized 触发
            pass

        #self.sig_repaint_inter.emit()


        #elif set_fall==0 and onfloor==0:

    def sleeping(self, act_name):
        """处理睡觉动画循环"""
        if not settings.is_sleeping:
            return

        # 获取睡觉动画配置
        onset = self.pet_conf.act_dict['fallasleep_onset']
        loop = self.pet_conf.act_dict['fallasleep_loop']

        # 播放入睡动画（如果还没播完）
        if settings.act_id == 0:
            prev_playid = settings.playid
            self.img_from_act(onset)
            # 发射信号触发 UI 重绘
            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()
            # 检测 img_from_act 是否停止更新 playid（说明动画到头了）
            if settings.playid == prev_playid:
                settings.act_id = 1
                settings.playid = 0
            return

        # 循环播放睡觉动画
        prev_playid = settings.playid
        self.img_from_act(loop)
        # 发射信号触发 UI 重绘
        if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
            self.sig_setimg_inter.emit()
        # 如果动画播放完毕，重置 playid 实现循环
        if settings.playid == prev_playid:
            settings.playid = 0

    def wake(self, act_name):
        """处理唤醒动画"""
        wake_act = self.pet_conf.act_dict['fallasleep_wake']
        prev_playid = settings.playid
        self.img_from_act(wake_act)
        # 发射信号触发 UI 重绘
        if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
            self.sig_setimg_inter.emit()
        # 检查动画是否播放完毕
        n_repeat = math.ceil(wake_act.frame_refresh / (self.pet_conf.interact_speed / 1000))
        img_list_expand = [item for item in wake_act.images for i in range(n_repeat)] * wake_act.act_num
        if settings.playid >= len(img_list_expand) or settings.playid == prev_playid:
            # 唤醒动画播放完毕，恢复正常状态
            # stop_interact() 会清除 is_sleeping、playid、act_id
            self.stop_interact()

    def startup_wake(self, act_name):
        """启动阶段醒来动画：播放 fallasleep_wake，期间锁定交互"""
        wake_act = self.pet_conf.act_dict['fallasleep_wake']
        prev_playid = settings.playid
        self.img_from_act(wake_act)
        if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
            self.sig_setimg_inter.emit()
        n_repeat = math.ceil(wake_act.frame_refresh / (self.pet_conf.interact_speed / 1000))
        img_list_expand = [item for item in wake_act.images for i in range(n_repeat)] * wake_act.act_num
        if settings.playid >= len(img_list_expand) or settings.playid == prev_playid:
            settings.is_starting_up = False
            import os as _os
            if _os.environ.get('DYBERPET_TEST_WAKE_PROBE'):
                print('[WAKE_PROBE] startup_wake finished -> is_starting_up=False')
            self.stop_interact()

    def wake_up(self):
        """唤醒睡觉的猫（由右键菜单调用）"""
        if not settings.is_sleeping or self.interact == 'wake':
            return
        self.start_interact('wake')

    def drop(self):
        #掉落
        #print("Dropping")

        ##print(dragspeedx)
        ##print(dragspeedy)
        #dropnext=pettop+info.gravity*dropa-info.gravity/2
        plus_y = settings.dragspeedy #+ self.pet_conf.dropspeed
        plus_x = settings.dragspeedx
        settings.dragspeedy = settings.dragspeedy + settings.gravity

        self.sig_move_inter.emit(plus_x, plus_y)

    def _get_frame_speed(self, act, frame_idx):
        """根据当前帧索引返回该帧的移动速度"""
        if not act.move_phases:
            return act.frame_move
        for phase in act.move_phases:
            if phase['start'] <= frame_idx <= phase['end']:
                speed = phase['speed']
                if isinstance(speed, (int, float)):
                    return speed
                parts = speed.split('->')
                s0, s1 = float(parts[0]), float(parts[1])
                if phase['end'] == phase['start']:
                    return s1
                t = (frame_idx - phase['start']) / (phase['end'] - phase['start'])
                return s0 + t * (s1 - s0)
        return 0.0

    def _move(self, act: QAction, frame_idx=0) -> None:
        """
        在 Thread 中发出移动Signal
        :param act: 动作
        :param frame_idx: 当前帧索引
        :return
        """
        plus_x = 0.
        plus_y = 0.
        direction = act.direction
        speed = self._get_frame_speed(act, frame_idx)

        if direction is None:
            pass
        else:
            if direction == 'right':
                plus_x = speed

            if direction == 'left':
                plus_x = -speed

            if direction == 'up':
                plus_y = -speed

            if direction == 'down':
                plus_y = speed

        if plus_x == 0 and plus_y == 0:
            pass
        else:
            self.sig_move_inter.emit(plus_x, plus_y)

    def use_item(self, item):
        # 物品 → 动画映射（共用动画的食物）
        feed_map = {
            '芝士汉堡': '汉堡',
            '牛奶': '酸奶',
        }
        # 播放该食物对应的专属动画
        feed_item = feed_map.get(item, item)
        act_name = f'feed_{feed_item}'

        # 如果正在播放喂食动画，不打断，只应用效果（效果在调用方已处理）
        if self.interact == 'animat' and self.act_name and self.act_name.startswith('feed_'):
            return

        # 检查 act_conf.json 里有没有这个动画
        if act_name in self.pet_conf.act_dict:
            self.start_interact('animat', act_name)
        else:
            # 没有专属动画，播放 stand
            self.start_interact('animat', 'stand')

        '''
        self.interact = 'animat' #None
        self.act_name = 'onfloor' #None
        settings.playid = 0
        settings.act_id = 0
        '''
        #self.stop_interact()
        return

    def use_clct(self, item):
        if item in self.pet_conf.act_name:
            self.start_interact('animat', item)
        elif item in self.pet_conf.acc_name:
            self.start_interact('anim_acc', item)
        else:
            self.stop_interact()

        return

    def followTarget(self, act_name):

        self.query_position.emit(act_name)
        distance = abs(self.main_pos[0] - self.target_pos[0])

        if distance < 5*self.pet_conf.left.frame_move:
            act = self.pet_conf.default
            self.img_from_act(act)
            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()

        else:
            act = [self.pet_conf.left, self.pet_conf.right][int(self.main_pos[0] < self.target_pos[0])]
            self.img_from_act(act)
            if settings.previous_img != settings.current_img or settings.previous_anchor != settings.current_anchor:
                self.sig_setimg_inter.emit()
                self._move(act)


    def receive_pos(self, main_pos, target_pos):
        self.main_pos = main_pos
        self.target_pos = target_pos




##############################
#          计划任务
##############################
class Scheduler_worker(QObject):
    sig_settext_sche = Signal(str, str, name='sig_settext_sche')
    sig_setact_sche = Signal(str, name='sig_setact_sche')
    sig_setstat_sche = Signal(str, int, name='sig_setstat_sche')
    sig_focus_end = Signal(name='sig_focus_end')
    sig_tomato_end = Signal(name='sig_tomato_end')
    sig_settime_sche = Signal(str, int, name='sig_settime_sche')
    sig_addItem_sche = Signal(int, name='sig_addItem_sche')
    sig_setup_bubble = Signal(dict, name='sig_setup_bubble')
    sig_wake_sche = Signal(name='sig_wake_sche')
    sig_poop_trigger = Signal(name='sig_poop_trigger')


    def __init__(self, parent=None):
        """
        Scheduler Module
        Time-related processor

        """
        super(Scheduler_worker, self).__init__(parent)
        #self.pet_conf = pet_conf
        self.is_killed = False
        self.is_paused = False
        #self.activated_times = 0
        self.new_task = False
        self.task_name = None
        self.n_tomato = None
        self.n_tomato_now = None
        self.focus_on = False
        self.tomato_list = []
        self.focus_time = 0
        self.tm_interval = 25
        self.tm_break = 5

        ''' Customized Pomodoro function deleted from v0.3.7
        pomodoro_conf = os.path.join(basedir, 'res/icons/Pomodoro.json')
        if os.path.isfile(pomodoro_conf):
            with open(pomodoro_conf, 'r', encoding='UTF-8') as _f:
                self.tm_config = json.load(_f)
        else:
            self.tm_config = {"title":"番茄钟",
                        "Description": "番茄工作法是一种时间管理方法，该方法使用一个定时器来分割出25分钟的工作时间和5分钟的休息时间，提高效率。",
                        "option_text": "想要执行",
                        "options":{"pomodoro": {
                                             "note_start":"新的番茄时钟开始了哦！加油！",
                                             "note_first":"个番茄时钟设定完毕！开始了哦！",
                                             "note_end":"叮叮~ 番茄时间到啦！休息5分钟！",
                                             "note_last":"叮叮~ 番茄时间全部结束啦！"
                                             }
                                  }
                        }
        '''
        self.pomodoro_text = {"name": self.tr("Pomodoro"),
                              "note_start": self.tr("The new Pomodoro has started! Let's go!"),
                              "note_first": self.tr(" Pomodoros have been set! Let's dive in!"),
                              "note_end": self.tr("Ding ding~ Pomodoro finished! Time for a 5-minute break!"),
                              "note_last": self.tr("Ding ding~ All Pomodoros completed! Great job!"),
                              "note_cancel": self.tr("Your Pomodoros have all been canceled!")}

        self.focus_text = {"name": self.tr("Focus Session"),
                           "note_start": self.tr("Your focus session has started!"),
                           "note_end": self.tr("Your focus session has completed!"),
                           "note_cancel": self.tr("Your focus session has been canceled!")}

        self.scheduler = QtScheduler()
        #self.scheduler.add_job(self.change_hp, 'interval', minutes=self.pet_conf.hp_interval)
        self.scheduler.add_job(self.change_hp, interval.IntervalTrigger(minutes=settings.HP_DECAY_MINUTES)) #self.pet_conf.hp_interval))
        #self.scheduler.add_job(self.change_em, 'interval', minutes=self.pet_conf.em_interval)
        self.scheduler.add_job(self.change_fv, interval.IntervalTrigger(minutes=1)) #self.pet_conf.fv_interval))
        # 自然唤醒定时器（每分钟检查一次，20% 概率唤醒，期望 5 分钟）
        self.scheduler.add_job(self.check_natural_wake, interval.IntervalTrigger(minutes=1))
        # 拉屎检查（每 N 分钟检查一次，随机概率触发）
        self.scheduler.add_job(
            self.check_poop,
            interval.IntervalTrigger(minutes=settings.POOP_CHECK_INTERVAL),
        )
        self.scheduler.start()


    def run(self):
        """Run Scheduler in a separate thread"""
        #time.sleep(10)
        if not settings.settingGood:
            settingBrokeNote = self.tr("*Setting config file broken. Setting is re-initialized.")
            self.show_dialogue('system', settingBrokeNote)
        else:
            settingBrokeNote = ""
        if not settings.pet_data.saveGood:
            saveBrokeNote = self.tr("*Game save file broken. Data is re-initialized.\nPlease load previous saved data to recover.")
            self.show_dialogue('system', saveBrokeNote)
        else:
            saveBrokeNote = ""
        #self.show_dialogue(greet_type, f'{greet_text}')
        self.send_greeting()
        
    
    def kill(self):
        self.is_paused = False
        self.is_killed = True
        self.scheduler.shutdown()


    def pause(self):
        self.is_paused = True
        self.scheduler.pause()


    def resume(self):
        self.is_paused = False
        self.scheduler.resume()

    def send_greeting(self):
        # 猫不会说话，统一显示"喵~"，不拼接 USERTAG
        self.sig_setup_bubble.emit({'message':'喵~', 'start_audio':'greeting_1', 'icon':None, '_no_usertag':True})


    def greeting(self, time):
        return 'greeting_1', self.tr("喵~")


    def show_dialogue(self, note_type, texts_toshow):
        # 排队 避免对话显示冲突
        while settings.showing_dialogue_now:
            time.sleep(1)
        settings.showing_dialogue_now = True
        #print('show_dialogue check')

        #for text_toshow in texts_toshow:
        self.sig_settext_sche.emit(note_type, texts_toshow) #text_toshow)
        #    time.sleep(3)
        #self.sig_settext_sche.emit('None')
        settings.showing_dialogue_now = False

    '''
    def item_drop(self, n_minutes):
        #print(n_minutes)
        nitems = n_minutes // 5
        remains = max(0, n_minutes % 5 - 1)
        chance_drop = random.choices([0,1], weights=(1-remains/5, remains/5))
        #print(chance_drop)
        nitems += chance_drop[0]
        #for test -----
        #nitems = 4
        #---------------
        if nitems > 0:
            self.sig_addItem_sche.emit(nitems)
    '''

    def add_tomato(self, n_tomato=None):

        if self.focus_on == False and self.n_tomato_now is None:
            self.n_tomato_now = n_tomato
            time_plus = 0 #25

            # 1-start
            task_text = 'tomato_first'
            time_torun = datetime.now() + timedelta(seconds=1)
            #self.scheduler.add_job(self.run_task, run_date=time_torun, args=[task_text])
            self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text])
            
            time_plus += self.tm_interval #25
            #1-end
            if n_tomato == 1:
                task_text = 'tomato_last'
            else:
                task_text = 'tomato_end'
            time_torun = datetime.now() + timedelta(minutes=time_plus) #minutes=time_plus)
            #self.scheduler.add_job(self.run_task, run_date=time_torun, args=[task_text])
            self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text], id='tomato_0_end')
            self.tomato_list.append('tomato_0_end')
            time_plus += self.tm_break #5

            # others start and end
            if n_tomato > 1:
                for i in range(1, n_tomato):
                    #start
                    task_text = 'tomato_start'
                    time_torun = datetime.now() + timedelta(minutes=time_plus) #minutes=time_plus)
                    #self.scheduler.add_job(self.run_task, run_date=time_torun, args=[task_text])
                    self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text], id='tomato_%s_start'%i)
                    time_plus += self.tm_interval #25
                    #end
                    if i == (n_tomato-1):
                        task_text = 'tomato_last'
                    else:
                        task_text = 'tomato_end'
                    time_torun = datetime.now() + timedelta(minutes=time_plus) #minutes=time_plus)
                    #self.scheduler.add_job(self.run_task, run_date=time_torun, args=[task_text])
                    self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text], id='tomato_%s_end'%i)
                    time_plus += self.tm_break #5
                    self.tomato_list.append('tomato_%s_start'%i)
                    self.tomato_list.append('tomato_%s_end'%i)

        ''' From v0.3.7, situations below won't happen
        elif self.focus_on:
            task_text = "focus_on"
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text])
        else:
            task_text = "tomato_exist"
            time_torun = datetime.now() + timedelta(seconds=1)
            #self.scheduler.add_job(self.run_task, run_date=time_torun, args=[task_text])
            self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun), args=[task_text])
        '''



    def run_tomato(self, task_text):
        text_toshow = ''
        #finished = False

        if task_text == 'tomato_start':
            self.tomato_timeleft = self.tm_interval #25
            self.scheduler.add_job(self.change_tomato, interval.IntervalTrigger(minutes=1), id='tomato_timer', replace_existing=True)
            self.sig_settime_sche.emit('tomato_start', self.tomato_timeleft)
            self.tomato_list = self.tomato_list[1:]
            text_toshow = self.pomodoro_text['note_start']

        elif task_text == 'tomato_first':
            self.scheduler.add_job(self.change_tomato, interval.IntervalTrigger(minutes=1), id='tomato_timer', replace_existing=True)
            self.tomato_timeleft = self.tm_interval #25
            self.sig_settime_sche.emit('tomato_start', self.tomato_timeleft)
            text_toshow = "%s%s"%(int(self.n_tomato_now), self.pomodoro_text['note_first'])

        elif task_text == 'tomato_end':
            self.tomato_timeleft = self.tm_break #5
            self.scheduler.add_job(self.change_tomato, interval.IntervalTrigger(minutes=1), id='tomato_timer', replace_existing=True)
            self.sig_settime_sche.emit('tomato_rest', self.tomato_timeleft)
            self.tomato_list = self.tomato_list[1:]
            text_toshow = self.pomodoro_text['note_end'] #'叮叮~ 番茄时间到啦！休息5分钟！'
            #finished = True

        elif task_text == 'tomato_last':
            try:
                self.scheduler.remove_job('tomato_timer')
            except:
                pass
            self.tomato_timeleft = 0
            self.n_tomato_now=None
            self.tomato_list = []
            self.sig_tomato_end.emit()
            self.sig_settime_sche.emit('tomato_end', self.tomato_timeleft)
            text_toshow = self.pomodoro_text['note_last']
            #finished = True

        elif task_text == 'tomato_cancel':
            self.n_tomato_now=None
            for iidd in self.tomato_list:
                self.scheduler.remove_job(iidd)
            self.tomato_list = []
            try:
                self.scheduler.remove_job('tomato_timer')
            except:
                pass
            self.tomato_timeleft = 0
            self.sig_settime_sche.emit('tomato_cencel', self.tomato_timeleft)
            self.sig_tomato_end.emit()
            text_toshow = self.pomodoro_text['note_cancel']

        ''' Theoretically, such situation won't exist from v0.3.7 on.
        elif task_text == 'tomato_exist':
            self.sig_tomato_end.emit()
            self.sig_settime_sche.emit('tomato_end', 0)
            text_toshow = "不行！还有 [%s] 在进行哦~"%(settings.current_tm_option)

        elif task_text == 'focus_on':
            self.sig_tomato_end.emit()
            self.sig_settime_sche.emit('tomato_end', 0)
            text_toshow = "不行！还有专注任务在进行哦~"
        '''
        if text_toshow:
            if task_text in ['tomato_start', 'tomato_first']:
                self.show_dialogue('start_tomato', text_toshow)

            elif task_text in ['tomato_end', 'tomato_last']:
                self.show_dialogue('end_tomato', text_toshow)

            elif task_text == 'tomato_cancel':
                self.show_dialogue('cancel_tomato', text_toshow)
        '''
        if finished:
            time.sleep(1)
            self.item_drop(n_minutes=30)
        '''
        #else:
        #    text_toshow = '叮叮~ 你的任务 [%s] 到时间啦！'%(task_text)

    def cancel_tomato(self):
        task_text = "tomato_cancel"
        time_torun_2 = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(self.run_tomato, date.DateTrigger(run_date=time_torun_2), args=[task_text])

    def change_hp(self):
        self.sig_setstat_sche.emit('hp', -1)

    def change_fv(self):
        self.sig_setstat_sche.emit('fv', 1)

    def change_tomato(self):
        self.tomato_timeleft += -1
        if self.tomato_timeleft <= 1:
            self.scheduler.remove_job('tomato_timer')
        self.sig_settime_sche.emit('tomato', self.tomato_timeleft)

    def change_focus(self):
        self.focus_time += -1
        if self.focus_time <= 1:
            self.scheduler.remove_job('focus_timer')
        self.sig_settime_sche.emit('focus', self.focus_time)


    def add_focus(self, time_range=None, time_point=None):
        ''' From v0.3.7, situations below won't happen
        if self.n_tomato_now is not None:
            task_text = "tomato_exist"
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text])

        elif self.focus_on:
            task_text = "focus_exist"
            time_torun = datetime.now() + timedelta(seconds=1)
            self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text])
        '''

        if time_range is not None:
            if sum(time_range) == 0:
                return
            else:
                self.focus_on = True
                task_text = "focus_start"
                time_torun = datetime.now() + timedelta(seconds=1)
                self.focus_time = int(time_range[0]*60 + time_range[1])
                self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text])

                task_text = "focus_end"
                time_torun = datetime.now() + timedelta(hours=time_range[0], minutes=time_range[1])
                self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text,self.focus_time], id='focus')

        ''' From v0.3.7, setting up by time_point has been deleted from UI
        elif time_point is not None:
            now = datetime.now()
            time_torun = datetime(year=now.year, month=now.month, day=now.day,
                                  hour=time_point[0], minute=time_point[1], second=0) #now.second)
            time_diff = time_torun - now
            self.focus_time = time_diff.total_seconds() // 60

            if time_diff <= timedelta(0):
                time_torun = time_torun + timedelta(days=1)
                self.focus_time += 24*60

                self.focus_on = True
                task_text = "focus_start_tomorrow"
                time_torun_2 = datetime.now() + timedelta(seconds=1)
                self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun_2), args=[task_text])

                task_text = "focus_end"
                self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text,self.focus_time], id='focus')
            else:
                self.focus_on = True
                task_text = "focus_start"
                time_torun_2 = datetime.now() + timedelta(seconds=1)
                self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun_2), args=[task_text])

                task_text = "focus_end"
                self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text,self.focus_time], id='focus')
        '''

    def run_focus(self, task_text, n_minutes=0):
        text_toshow = ''
        #finished = False
        ''' From v0.3.7, situations below won't happen
        if task_text == 'tomato_exist':
            self.sig_focus_end.emit()
            self.sig_settime_sche.emit('focus_end', 0)
            text_toshow = '不行！还有 [%s] 在进行哦~'%(settings.current_tm_option)

        elif task_text == 'focus_exist':
            self.sig_focus_end.emit()
            self.sig_settime_sche.emit('focus_end', 0)
            text_toshow = "不行！还有专注任务在进行哦~"
        '''
        if task_text == 'focus_start':
            if self.focus_time > 1:
                self.scheduler.add_job(self.change_focus, interval.IntervalTrigger(minutes=1), id='focus_timer', replace_existing=True)
            #elif self.focus_time < 1:
            #    print(self.focus_time)
                #focus_time_sec = int()
            self.sig_settime_sche.emit('focus_start', self.focus_time)
            text_toshow = self.focus_text['note_start'] #"你的专注任务开始啦！"


        elif task_text == 'focus_end':
            self.focus_time = 0
            try:
                self.scheduler.remove_job('focus_timer')
            except:
                pass
            self.sig_settime_sche.emit('focus_end', self.focus_time)
            self.focus_on = False
            self.sig_focus_end.emit()
            text_toshow = self.focus_text['note_end'] #"你的专注任务结束啦！"
            #finished = True


        elif task_text == 'focus_cancel':
            self.focus_time = 0
            try:
                self.scheduler.remove_job('focus_timer')
            except:
                pass
            self.sig_settime_sche.emit('focus_cancel', self.focus_time)
            self.sig_focus_end.emit()
            self.focus_on = False
            text_toshow = self.focus_text['note_cancel'] #"你的专注任务取消啦！"
            #finished = True
        
        if text_toshow:
            if task_text == 'focus_start':
                self.show_dialogue('start_focus', text_toshow)

            elif task_text == 'focus_end':
                self.show_dialogue('end_focus', text_toshow)

            elif task_text == 'focus_cancel':
                self.show_dialogue('cancel_focus', text_toshow)

        ''' From v0.3.7, situations below won't happen
        elif task_text == 'focus_start_tomorrow':
            if self.focus_time > 1:
                self.scheduler.add_job(self.change_focus, interval.IntervalTrigger(minutes=1), id='focus_timer', replace_existing=True)
            self.sig_settime_sche.emit('focus_start', self.focus_time)
            text_toshow = "专注任务开始啦！\n但设定在明天，请确认无误哦~"

        elif task_text == 'focus_pause':
            try:
                self.scheduler.remove_job('focus_timer')
            except:
                pass
            #self.sig_settime_sche.emit('focus_end', self.focus_time)
            #self.sig_focus_end.emit()
            #self.focus_on = False
            text_toshow = "你的专注任务暂停啦！"

        elif task_text == 'focus_resume':
            if self.focus_time > 1:
                self.scheduler.add_job(self.change_focus, interval.IntervalTrigger(minutes=1), id='focus_timer', replace_existing=True)

            self.sig_settime_sche.emit('focus', self.focus_time)
            text_toshow = "你的专注任务继续进行啦！"
        '''

    ''' Pause function deleted from v0.3.7
    def pause_focus(self):
        try:
            self.scheduler.remove_job('focus')
        except:
            pass
        task_text = "focus_pause"
        time_torun_2 = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun_2), args=[task_text])

    def resume_focus(self, remains, total):
        task_text = "focus_resume"
        self.focus_time = remains
        time_torun = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text])

        task_text = "focus_end"
        time_torun = datetime.now() + timedelta(minutes=remains)
        self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun), args=[task_text,total], id='focus')
    '''
    def cancel_focus(self, time_past):
        try:
            self.scheduler.remove_job('focus')
        except:
            pass
        task_text = "focus_cancel"
        time_torun_2 = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(self.run_focus, date.DateTrigger(run_date=time_torun_2), args=[task_text,time_past])

    def check_natural_wake(self):
        """检查是否自然唤醒"""
        if not settings.is_sleeping:
            return

        # 20% 概率自然唤醒
        if random.random() < 0.2:
            self.wake_up()

    def wake_up(self):
        """唤醒睡觉的猫"""
        if not settings.is_sleeping:
            return

        # 通过信号触发 Interaction_worker 播放醒来动画
        # is_sleeping 由 wake 方法在动画播放完毕后清除
        self.sig_wake_sche.emit()

    def check_poop(self):
        """定时检查是否触发拉屎"""
        if not settings.poop_enabled:
            return

        # 30% 概率触发
        if random.random() >= settings.POOP_PROBABILITY:
            return

        # 状态检查：必须在地面、不在睡觉、不在启动、不在弹跳
        if settings.onfloor != 1:
            return
        if settings.is_sleeping:
            return
        if settings.is_starting_up:
            return
        if settings.bouncing:
            return

        self.sig_poop_trigger.emit()

    ''' Reminder function deleted from v0.3.7
    def add_remind(self, texts, time_range=None, time_point=None, repeat=False):
        if time_point is not None:
            if repeat:
                certain_minute = int(time_point[1])
                self.scheduler.add_job(self.run_remind,
                                       cron.CronTrigger(minute=certain_minute),
                                       args=[texts])
            else:
                certain_day = datetime.now().day
                certain_hour = int(time_point[0])
                certain_minute = int(time_point[1])
                if certain_hour < datetime.now().hour:
                    certain_day = (datetime.now() + timedelta(days=1)).day
                self.scheduler.add_job(self.run_remind,
                                       cron.CronTrigger(day=certain_day,
                                                        hour=certain_hour,
                                                        minute=certain_minute),
                                       args=[texts])

        elif time_range is not None:
            if repeat:
                interval_minute = int(time_range[1])
                self.scheduler.add_job(self.run_remind,
                                       interval.IntervalTrigger(minutes=interval_minute),
                                       args=[texts])
            else:
                if sum(time_range) == 0:
                    return
                else:
                    time_torun = datetime.now() + timedelta(hours=time_range[0], minutes=time_range[1])
                    self.scheduler.add_job(self.run_remind,
                                           date.DateTrigger(run_date=time_torun),
                                           args=[texts])

        time_torun_2 = datetime.now() + timedelta(seconds=1)
        self.scheduler.add_job(self.run_remind,
                               date.DateTrigger(run_date=time_torun_2),
                               args=['remind_start'])

    def run_remind(self, task_text):
        if task_text == 'remind_start':
            text_toshow = "提醒事项设定完成！"
        else:
            text_toshow = '叮叮~ 时间到啦\n[ %s ]'%task_text
        
        self.show_dialogue('clock_remind',text_toshow)
    '''

        





