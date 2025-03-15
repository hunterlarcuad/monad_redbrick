import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
import math
import re # noqa
from datetime import datetime # noqa

from DrissionPage import ChromiumOptions
from DrissionPage import Chromium
from DrissionPage._elements.none_element import NoneElement

from fun_utils import ding_msg
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import format_ts
from fun_utils import time_difference
from fun_utils import seconds_to_hms

from conf import DEF_LOCAL_PORT
from conf import DEF_INCOGNITO
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_NUM_TRY
from conf import NUM_MAX_TRY_PER_DAY
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_BROWSER
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS
from conf import DEF_OKX_EXTENSION_PATH
from conf import EXTENSION_ID_OKX
from conf import DEF_PWD

from conf import DEF_PATH_DATA_PURSE
from conf import DEF_HEADER_PURSE

from conf import TZ_OFFSET
from conf import DEL_PROFILE_DIR

from conf import logger

"""
2025.03.12
https://redbrick.land/web3-portal?tab=monad_testnet
"""

# Wallet balance
DEF_INSUFFICIENT = -1
DEF_SUCCESS = 0
DEF_FAIL = 1

# Mint would exceed wallet limit
DEF_EXCEED_LIMIT = 10
# Price too high
DEF_PRICE_TOO_HIGH = 11

# output
IDX_NUM_POINT = 1
IDX_CLAIM_DATE = 2
IDX_NEXT_CLAIM = 3
IDX_NUM_TRY = 4
IDX_UPDATE = 5
FIELD_NUM = IDX_UPDATE + 1


class MonadTask():
    def __init__(self) -> None:
        self.args = None

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}

        self.dic_purse = {}

        self.purse_load()

    def set_args(self, args):
        self.args = args
        self.is_update = False

    def __del__(self):
        self.status_save()

    def purse_load(self):
        self.file_purse = f'{DEF_PATH_DATA_PURSE}/purse.csv'
        self.dic_purse = load_file(
            file_in=self.file_purse,
            idx_key=0,
            header=DEF_HEADER_PURSE
        )

    def status_load(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.browser:
                try:
                    self.browser.quit()
                except Exception as e: # noqa
                    # logger.info(f'[Close] Error: {e}')
                    pass

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        # Settings.singleton_tab_obj = True

        profile_path = s_profile

        # 是否设置无痕模式
        if DEF_INCOGNITO:
            co = ChromiumOptions().incognito(True)
        else:
            co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)

        co.set_argument('--accept-lang', 'en-US')  # 设置语言为英语（美国）
        co.set_argument('--lang', 'en-US')

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        # 关闭沙盒模式
        # co.set_argument('--no-sandbox')

        # popups支持的取值
        # 0：允许所有弹窗
        # 1：只允许由用户操作触发的弹窗
        # 2：禁止所有弹窗
        # co.set_pref(arg='profile.default_content_settings.popups', value='0')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        # 获取当前工作目录
        current_directory = os.getcwd()

        # 检查目录是否存在
        if os.path.exists(os.path.join(current_directory, DEF_OKX_EXTENSION_PATH)): # noqa
            logger.info(f'okx plugin path: {DEF_OKX_EXTENSION_PATH}')
            co.add_extension(DEF_OKX_EXTENSION_PATH)
        else:
            print("okx plugin directory is not exist. Exit!")
            sys.exit(1)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa

        try:
            self.browser = Chromium(co)
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def is_exist(self, s_title, s_find, match_type):
        b_ret = False
        if match_type == 'fuzzy':
            if s_title.find(s_find) >= 0:
                b_ret = True
        else:
            if s_title == s_find:
                b_ret = True

        return b_ret

    def okx_secure_wallet(self):
        tab = self.browser.latest_tab
        # Secure your wallet
        ele_info = tab.ele('Secure your wallet')
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_secure_wallet', 'Secure your wallet')
            ele_btn = tab.ele('Password', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.browser.wait(1)
                self.logit('okx_secure_wallet', 'Select Password')

                # Next
                ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.browser.wait(1)
                    self.logit('okx_secure_wallet', 'Click Next')
                    return True
        return False

    def okx_set_pwd(self):
        tab = self.browser.latest_tab
        # Set password
        ele_info = tab.ele('Set password', timeout=2)
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_set_pwd', 'Set Password')
            ele_input = tab.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit('okx_set_pwd', 'Input Password')
                tab.actions.move_to(ele_input).click().type(DEF_PWD)
            self.browser.wait(1)
            ele_input = tab.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Re-enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                tab.actions.move_to(ele_input).click().type(DEF_PWD)
                self.logit('okx_set_pwd', 'Re-enter Password')
            self.browser.wait(1)
            ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit('okx_set_pwd', 'Password Confirmed [OK]')
                self.browser.wait(10)
                return True
        return False

    def okx_bulk_import_private_key(self, s_key):
        tab = self.browser.latest_tab
        ele_btn = tab.ele('@@tag()=div@@class:_typography@@text():Bulk import private key', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            ele_btn.click(by_js=True)
            self.logit('okx_bulk_import_private_key', 'Click ...')

            tab = self.browser.get_tab(self.browser.latest_tab.tab_id)

            ele_btn = tab.ele('@@tag()=i@@id=okdDialogCloseBtn', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Close pwd input box ...')
                ele_btn.click(by_js=True)

            ele_btn = tab.ele('@@tag()=div@@data-testid=okd-select-reference-value-box', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Select network ...')
                ele_btn.click(by_js=True)

            ele_btn = tab.ele('@@tag()=div@@class:_typography@@text()=EVM networks', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Select EVM networks ...')
                ele_btn.click(by_js=True)

            ele_input = tab.ele('@@tag()=textarea@@id:pk-input@@placeholder:private', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit(None, 'Input EVM key ...')
                tab.actions.move_to(ele_input).click().type(s_key) # noqa
                self.browser.wait(5)

    def init_okx(self, is_bulk=False):
        """
        chrome-extension://jiofmdifioeejeilfkpegipdjiopiekl/popup/index.html
        """
        s_url = f'chrome-extension://{EXTENSION_ID_OKX}/home.html'

        tab = self.browser.new_tab(s_url)
        self.browser.wait(1)

        self.browser.close_tabs(tab, others=True)
        self.browser.wait(2)

        self.logit('init_okx', f'tabs_count={self.browser.tabs_count}')

        self.save_screenshot(name='okx_1.jpg')

        tab = self.browser.latest_tab
        ele_info = tab.ele('@@tag()=div@@class:balance', timeout=2) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.text
            self.logit('init_okx', f'Account balance: {s_info}') # noqa
            return True

        ele_btn = tab.ele('Import wallet', timeout=2)
        if not isinstance(ele_btn, NoneElement):
            # Import wallet
            self.logit('init_okx', 'Import wallet ...')
            ele_btn.click(by_js=True)

            self.browser.wait(1)
            ele_btn = tab.ele('Seed phrase or private key', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                # Import wallet
                self.logit('init_okx', 'Select Seed phrase or private key ...') # noqa
                ele_btn.click(by_js=True)
                self.browser.wait(1)

                s_key = self.dic_purse[self.args.s_profile][1]
                if len(s_key.split()) == 1:
                    # Private key
                    self.logit('init_okx', 'Import By Private key')
                    ele_btn = tab.ele('Private key', timeout=2)
                    if not isinstance(ele_btn, NoneElement):
                        # 点击 Private key Button
                        self.logit('init_okx', 'Select Private key')
                        ele_btn.click(by_js=True)
                        self.browser.wait(1)
                        ele_input = tab.ele('@class:okui-input-input input-textarea ta', timeout=2) # noqa
                        if not isinstance(ele_input, NoneElement):
                            # 使用动作，输入完 Confirm 按钮才会变成可点击状态
                            tab.actions.move_to(ele_input).click().type(s_key) # noqa
                            self.browser.wait(5)
                            self.logit('init_okx', 'Input Private key')
                    is_bulk = True
                    if is_bulk:
                        self.okx_bulk_import_private_key(s_key)
                else:
                    # Seed phrase
                    self.logit('init_okx', 'Import By Seed phrase')
                    words = s_key.split()

                    # 输入助记词需要最大化窗口，否则最后几个单词可能无法输入
                    tab.set.window.max()

                    ele_inputs = tab.eles('.mnemonic-words-inputs__container__input', timeout=2) # noqa
                    if not isinstance(ele_inputs, NoneElement):
                        self.logit('init_okx', 'Input Seed phrase')
                        for i in range(len(ele_inputs)):
                            ele_input = ele_inputs[i]
                            tab.actions.move_to(ele_input).click().type(words[i]) # noqa
                            self.logit(None, f'Input word [{i+1}/{len(words)}]') # noqa
                            self.browser.wait(1)

                # Confirm
                max_wait_sec = 10
                i = 1
                while i < max_wait_sec:
                    tab = self.browser.latest_tab
                    ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
                    self.logit('init_okx', f'To Confirm ... {i}/{max_wait_sec}') # noqa
                    if not isinstance(ele_btn, NoneElement):
                        if ele_btn.states.is_enabled is False:
                            self.logit(None, 'Confirm Button is_enabled=False')
                        else:
                            if ele_btn.states.is_clickable:
                                ele_btn.click(by_js=True)
                                self.logit('init_okx', 'Confirm Button is clicked') # noqa
                                self.browser.wait(1)
                                break
                            else:
                                self.logit(None, 'Confirm Button is_clickable=False') # noqa

                    i += 1
                    self.browser.wait(1)
                # 未点击 Confirm
                if i >= max_wait_sec:
                    self.logit('init_okx', 'Confirm Button is not found [ERROR]') # noqa

                # 导入私钥有此选择页面，导入助记词则没有此选择过程
                # Select network and Confirm
                ele_info = tab.ele('Select network', timeout=2)
                if not isinstance(ele_info, NoneElement):
                    self.logit('init_okx', 'Select network ...')
                    ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.browser.wait(1)
                        self.logit('init_okx', 'Select network finish')

                self.okx_secure_wallet()

                # Set password
                is_success = self.okx_set_pwd()

                # Import successful
                tab = self.browser.latest_tab
                ele_info = tab.ele('@@tag()=div@@text():Import successful', timeout=2) # noqa
                if not isinstance(ele_info, NoneElement):
                    s_info = ele_info.text.replace('\n', ';')
                    self.logit(None, f'[Info] {s_info}') # noqa

                    # Don't click OK button, or chrome will exit.
                    # ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text()=OK', timeout=2) # noqa
                    # if not isinstance(ele_btn, NoneElement):
                    #     ele_btn.click(by_js=True)
                    #     self.browser.wait(1)

                # Start your Web3 journey
                self.browser.wait(1)
                self.save_screenshot(name='okx_2.jpg')
                tab = self.browser.latest_tab
                ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text():Start', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.logit('init_okx', 'import wallet success')
                    self.save_screenshot(name='okx_3.jpg')
                    self.browser.wait(2)

                if is_success:
                    return True
        else:
            ele_info = tab.ele('Your portal to Web3', timeout=2)
            if not isinstance(ele_info, NoneElement):
                self.logit('init_okx', 'Input password to unlock ...')
                s_path = '@@tag()=input@@data-testid=okd-input@@placeholder:Enter' # noqa
                ele_input = tab.ele(s_path, timeout=2) # noqa
                if not isinstance(ele_input, NoneElement):
                    tab.actions.move_to(ele_input).click().type(DEF_PWD)
                    if ele_input.value != DEF_PWD:
                        self.logit('init_okx', '[ERROR] Fail to input passwrod !') # noqa
                        tab.set.window.max()
                        return False

                    self.browser.wait(1)
                    ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text():Unlock', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.browser.wait(1)

                        self.logit('init_okx', 'login success')
                        self.save_screenshot(name='okx_2.jpg')

                        return True
            else:
                ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.browser.wait(1)
                else:
                    ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.browser.wait(1)
                    else:
                        self.logit('init_okx', '[ERROR] What is this ... [quit]') # noqa
                        self.browser.quit()

        self.logit('init_okx', 'login failed [ERROR]')
        return False

    def save_screenshot(self, name):
        tab = self.browser.latest_tab
        # 对整页截图并保存
        # tab.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        tab.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def is_task_complete(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        if s_profile not in self.dic_status:
            return False

        claimed_date = self.dic_status[s_profile][idx_status]
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET) # noqa
        if date_now != claimed_date:
            return False
        else:
            return True

    def update_status(self, idx_status, s_value):
        update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        def init_status():
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
            ]
            for i in range(1, FIELD_NUM):
                self.dic_status[self.args.s_profile].append('')

        if self.args.s_profile not in self.dic_status:
            init_status()
        if len(self.dic_status[self.args.s_profile]) != FIELD_NUM:
            init_status()
        if self.dic_status[self.args.s_profile][idx_status] == s_value:
            return

        self.dic_status[self.args.s_profile][idx_status] = s_value
        self.dic_status[self.args.s_profile][IDX_UPDATE] = update_time

        self.status_save()
        self.is_update = True

    def get_status_by_idx(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        s_val = ''
        lst_pre = self.dic_status.get(s_profile, [])
        if len(lst_pre) == FIELD_NUM:
            try:
                s_val = int(lst_pre[idx_status])
            except: # noqa
                pass

        return s_val

    def get_pre_num_try(self, s_profile=None):
        num_try_pre = 0

        s_val = self.get_status_by_idx(IDX_NUM_TRY, s_profile)

        try:
            num_try_pre = int(s_val)
        except: # noqa
            pass

        return num_try_pre

    def update_num_try(self, s_profile=None):
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET)
        s_update = self.get_status_by_idx(-1, s_profile)
        if len(s_update) > 10:
            date_update = s_update[:10]
        else:
            date_update = ''
        if date_now != date_update:
            num_try_cur = 1
        else:
            num_try_pre = self.get_pre_num_try(s_profile)
            num_try_cur = num_try_pre + 1

        self.update_status(IDX_NUM_TRY, str(num_try_cur))

    def update_point_num(self, s_profile=None):
        tab = self.browser.latest_tab
        ele_blk = tab.ele('@@tag()=div@@class:Profile_container', timeout=1) # noqa
        if not isinstance(ele_blk, NoneElement):
            tab.actions.move_to(ele_blk)

        ele_info = tab.ele('@@tag()=p@@class:Typography@@text()=Point', timeout=1) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.next().text
            self.logit(None, f'Point: {s_info}')
        else:
            s_info = None

        s_val = self.get_status_by_idx(IDX_NUM_POINT)
        try:
            s_val = int(s_info)
        except: # noqa
            pass
        self.update_status(IDX_NUM_POINT, s_val)

    def update_date(self, idx_status, update_ts=None):
        if not update_ts:
            update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        claim_date = update_time[:10]

        self.update_status(idx_status, claim_date)

    def wait_popup(self, n_wait_sec=30):
        """
        wait until max_wait_sec or the popup window appear
        """
        # n_wait_sec = 10
        j = 0
        while j < n_wait_sec:
            j += 1
            self.browser.wait(1)
            self.logit('wait_popup', f'Wait popup window {j}/{n_wait_sec}')

            if len(self.browser.tab_ids) == 2:
                self.browser.wait(1)
                return True

        self.logit('wait_popup', 'Fail to load popup window')

        return False

    def wait_cofirm(self, n_wait_sec=30):
        """
        wait until max_wait_sec or the popup window disappear
        """
        # n_wait_sec = 10
        j = 0
        while j < n_wait_sec:
            j += 1
            self.browser.wait(1)
            self.logit('wait_cofirm', f'Wait popup disappear {j}/{n_wait_sec}')

            if len(self.browser.tab_ids) != 2:
                self.browser.wait(1)
                break

    def okx_connect(self):
        # OKX Wallet Connect
        self.save_screenshot(name='page_wallet_connect.jpg')
        if len(self.browser.tab_ids) == 2:
            tab_new = self.browser.latest_tab
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.browser.wait(1)
                return True
        return False

    def okx_confirm(self):
        # OKX Wallet Confirm
        self.save_screenshot(name='page_wallet_confirm.jpg')
        if len(self.browser.tab_ids) != 2:
            return False

        tab_new = self.browser.latest_tab
        max_wait_sec = 30
        i = 1
        while i < max_wait_sec:
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
            self.logit(None, f'Wait To Confirm ... {i}/{max_wait_sec}') # noqa
            if not isinstance(ele_btn, NoneElement):
                if ele_btn.states.is_enabled is False:
                    self.logit(None, 'Confirm Button is_enabled=False')
                else:
                    if ele_btn.states.is_clickable:
                        ele_btn.click(by_js=True)
                        self.logit(None, 'Confirm Button is clicked') # noqa
                        tab_new.wait(1)
                        return True
                    else:
                        self.logit(None, 'Confirm Button is_clickable=False') # noqa

            i += 1
            tab_new.wait(1)
        # 未点击 Confirm
        self.logit(None, 'Confirm Button is not found [ERROR]') # noqa
        return False

    def okx_signature(self):
        # OKX Wallet Signature request
        self.save_screenshot(name='page_wallet_signature.jpg')
        if len(self.browser.tab_ids) == 2:
            self.logit(None, 'OKX Wallet Signature request ...') # noqa
            tab_new = self.browser.latest_tab
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.wait_cofirm()
                self.logit(None, 'OKX Wallet Signature request Confirmed [OK]') # noqa
                return True
        return False

    def shadow_connect_wallet(self):
        """
        shadow-root
        Connect Wallet
        list
        """
        tab = self.browser.latest_tab
        ele_blk_1 = tab.ele('@@tag()=w3m-modal@@class=open', timeout=2) # noqa
        if not isinstance(ele_blk_1, NoneElement):
            tab_shadow_1 = ele_blk_1.shadow_root
            ele_blk_2 = tab_shadow_1.ele('@@tag()=wui-flex', timeout=2) # noqa
            if not isinstance(ele_blk_2, NoneElement):

                ele_blk_3 = ele_blk_2.ele('@@tag()=wui-card', timeout=2) # noqa
                if not isinstance(ele_blk_3, NoneElement):

                    ele_blk_4 = ele_blk_3.ele('@@tag()=w3m-router', timeout=2) # noqa
                    if not isinstance(ele_blk_4, NoneElement):
                        tab_shadow_router = ele_blk_4.shadow_root

                        ele_blk_5 = tab_shadow_router.ele('@@tag()=div', timeout=2) # noqa
                        if not isinstance(ele_blk_5, NoneElement):
                            ele_blk_6 = ele_blk_5.ele('@@tag()=w3m-connect-view', timeout=2) # noqa
                            if not isinstance(ele_blk_6, NoneElement):
                                tab_shadow_view = ele_blk_6.shadow_root

                                ele_blk_7 = tab_shadow_view.ele('@@tag()=wui-flex', timeout=2) # noqa
                                if not isinstance(ele_blk_2, NoneElement):

                                    ele_blk_8 = tab_shadow_view.ele('@@tag()=w3m-wallet-login-list', timeout=2) # noqa
                                    if not isinstance(ele_blk_8, NoneElement):
                                        tab_shadow_list = ele_blk_8.shadow_root

                                        ele_blk_9 = tab_shadow_list.ele('@@tag()=wui-flex', timeout=2) # noqa
                                        if not isinstance(ele_blk_9, NoneElement):

                                            ele_blk_10 = ele_blk_9.ele('@@tag()=w3m-connector-list', timeout=2) # noqa
                                            if not isinstance(ele_blk_10, NoneElement):
                                                tab_shadow_conn = ele_blk_10.shadow_root
                                                ele_blk_11 = tab_shadow_conn.ele('@@tag()=wui-flex', timeout=2) # noqa
                                                if not isinstance(ele_blk_11, NoneElement):
                                                    ele_blk_12 = ele_blk_11.ele('@@tag()=w3m-connect-injected-widget', timeout=2) # noqa
                                                    if not isinstance(ele_blk_12, NoneElement):
                                                        tab_shadow_okx = ele_blk_12.shadow_root
                                                        ele_btn_okx = tab_shadow_okx.ele('@@tag()=wui-flex', timeout=2) # noqa
                                                        if not isinstance(ele_btn_okx, NoneElement):
                                                            ele_btn_okx.click()
                                                            if self.wait_popup():
                                                                self.okx_connect()
                                                                self.wait_cofirm()
                                                                return True
        return False

    def connect_wallet(self):
        tab = self.browser.latest_tab
        ele_info = tab.ele('@@tag()=p@@text():Connect Wallet', timeout=1) # noqa
        if not isinstance(ele_info, NoneElement):
            self.browser.wait(1)
            self.logit(None, f'[Info] {ele_info.text}')
            ele_btn = tab.ele('@@tag()=button@@text()=Sign', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.browser.wait(1)
                self.logit(None, 'Click Sign Button')

                if self.wait_popup():
                    self.okx_confirm()
                    self.wait_cofirm()

    def account_register(self):
        tab = self.browser.latest_tab
        ele_info = tab.ele('@@tag()=p@@text():There is no account registered', timeout=1) # noqa
        if not isinstance(ele_info, NoneElement):
            self.browser.wait(1)
            self.logit(None, f'[Info] {ele_info.text}')
            ele_btn = tab.ele('@@tag()=button@@text()=New account', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.browser.wait(1)
                self.logit(None, 'Click New account Button')

                if self.wait_popup():
                    self.okx_confirm()
                    self.wait_cofirm()

    def give_nickname(self):
        tab = self.browser.latest_tab
        ele_info = tab.ele('@@tag()=h1@@text():Give yourself a nickname', timeout=1) # noqa
        if not isinstance(ele_info, NoneElement):
            self.browser.wait(1)
            self.logit(None, 'Give yourself a nickname ...')
            ele_btn = tab.ele('@@tag()=button@@type=submit@@text()=Next', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.browser.wait(1)

                ele_info = tab.ele('@@tag()=div@@class:SignUpFinishPopup_title', timeout=1) # noqa
                if not isinstance(ele_info, NoneElement):
                    s_info = ele_info.text.replace('\n', ';')
                    self.logit(None, f'[Register Success] {s_info}') # noqa
                    return True

        return False

    def mint_game_pass(self):
        tab = self.browser.latest_tab

        ele_blk = tab.ele('@@tag()=div@@class:rounded-@@text():Get your Game Pass', timeout=1) # noqa
        if not isinstance(ele_blk, NoneElement):
            tab.actions.move_to(ele_blk)
            ele_btn = ele_blk.ele('@@tag()=button@@class:NButton_container@@text():Game Pass', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                s_info = ele_btn.text
                # Mint Game Pass Free
                # Game Pass Already Minted
                self.logit(None, f'Button.text: {s_info}')

                if s_info.find('Minted') >= 0:
                    return True

                if not ele_btn.click():
                    self.logit(None, 'Fail to Click Mint Game Pass Free Button')
                    return False
                self.browser.wait(1)
                self.logit(None, 'Click Mint Game Pass Free Button')

                # Failed to fetch
                # ele_info = tab.ele('@@tag()=span@@class:Typography@@text()=Failed to fetch', timeout=1) # noqa
                ele_info = tab.ele('@@text()=Failed to fetch', timeout=1) # noqa
                if not isinstance(ele_info, NoneElement):
                    s_info = ele_info.text
                    self.logit(None, f'[WARNING] {ele_info.html}')
                    self.logit(None, f'[WARNING] {s_info}')

                if self.wait_popup():
                    self.okx_confirm()
                    self.wait_cofirm()

                n_wait_sec = 20
                j = 0
                while j < n_wait_sec:
                    j += 1
                    self.browser.wait(1)
                    self.logit(None, f'Wait minting msg {j}/{n_wait_sec}')

                    ele_info = tab.ele('@@tag()=p@@text():Refill it with Play Credits and start competing!', timeout=1) # noqa
                    if not isinstance(ele_info, NoneElement):
                        self.logit(None, 'minted your Game Pass [OK]')

                        ele_btn = tab.ele('@@tag()=button@@text()=Done', timeout=1) # noqa
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            self.browser.wait(1)

                        return True

        return False

    def get_next_claim_ts(self, sin):
        """
        There may be abnormal prompts
        -22:-55:-23
        """
        fields = sin.split(':')
        if len(fields) != 3:
            return None

        try:
            # 解析输入的时间字符串
            h, m, s = map(int, fields)

            # 如果值为负，取绝对值
            h, m, s = abs(h), abs(m), abs(s)

            # 将倒计时转换为总秒数
            countdown_seconds = h * 3600 + m * 60 + s

            # 获取当前时间的时间戳
            current_timestamp = int(datetime.now().timestamp())

            # 将倒计时的总秒数加到当前时间戳上
            target_timestamp = current_timestamp + countdown_seconds
        except: # noqa
            return None

        # 返回计算后的时间戳
        return target_timestamp

    def daily_checkin(self):
        tab = self.browser.latest_tab

        def get_claim_status():
            self.browser.wait(5)
            ele_info = tab.ele('@@tag()=p@@class:rounded-', timeout=1) # noqa
            if not isinstance(ele_info, NoneElement):
                s_info = ele_info.text
                self.logit(None, f'Daily check-in time countdown: {s_info}')
                next_claim_ts = self.get_next_claim_ts(s_info)
                if next_claim_ts is None:
                    return False
                else:
                    next_claim_ts += 30
                    next_claim_time = format_ts(next_claim_ts, 2, TZ_OFFSET)
                    self.update_status(IDX_NEXT_CLAIM, next_claim_time)
                    self.update_date(IDX_CLAIM_DATE)
                    self.update_point_num()
                    return True

        ele_blk = tab.ele('@@tag()=div@@class:rounded-@@text():Daily Check-In', timeout=1) # noqa
        if not isinstance(ele_blk, NoneElement):
            tab.actions.move_to(ele_blk)
            ele_btn = ele_blk.ele('@@tag()=button@@text()=Claim', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                if not ele_btn.click():
                    self.logit(None, '[Daily Check-In] Fail to Click Claim Button')
                    return False
                self.browser.wait(1)
                self.logit(None, '[Daily Check-In] Click Claim Button ...')

                if self.shadow_connect_wallet():
                    return False

                if self.wait_popup():
                    self.okx_confirm()
                    self.wait_cofirm()

                    n_wait_sec = 15
                    j = 0
                    while j < n_wait_sec:
                        j += 1
                        self.browser.wait(1)
                        self.logit(None, f'Wait to get time countdown {j}/{n_wait_sec}')

                        if get_claim_status():
                            self.logit(None, 'Daily Check-In Success ✅')
                            return True

                return False
            else:
                return get_claim_status()

        return False

    def monad_redbrick_login(self):
        """
        """
        for i in range(1, DEF_NUM_TRY+1):
            self.logit('monad_redbrick_login', f'try_i={i}/{DEF_NUM_TRY}')

            tab = self.browser.latest_tab
            ele_btn = tab.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.browser.wait(1)
                self.logit(None, 'Cancel Unknown transaction')

            s_url = 'https://redbrick.land/web3-portal?tab=monad_testnet' # noqa
            tab.get(s_url)
            # self.browser.wait.load_start()
            self.browser.wait(3)

            self.logit('monad_redbrick_login', f'tabs_count={self.browser.tabs_count}') # noqa

            # 钱包连接状态
            ele_btn = tab.ele('@@tag()=div@@class:Profile_container@@data-cy=Header_Profile', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                s_info = ele_btn.text
                if 'Sign-in' == s_info:
                    self.logit(None, 'Need to Sign-in ...') # noqa
                    ele_btn.click()
                    self.browser.wait(1)
                    ele_btn = tab.ele('@@tag()=button@@text()=Continue with wallet', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.logit(None, 'Continue with wallet ...') # noqa

                        self.shadow_connect_wallet()

                    self.connect_wallet()
                    self.account_register()
                    self.give_nickname()
                    continue
                else:
                    # 钱包已连接
                    self.logit(None, 'Wallet is connected')
                    # 如果有 Give yourself a nickname 窗口，则处理 
                    self.give_nickname()
                    return True
            else:
                self.logit(None, 'Fail to get login status html element [ERROR]')
                return False

    def okx_cancel(self):
        # OKX Wallet Cancel Uncomplete request
        if len(self.browser.tab_ids) == 2:
            tab_id = self.browser.latest_tab
            tab_new = self.browser.get_tab(tab_id)
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                tab_new.wait(1)
                self.logit(None, 'Uncomplete request. Cancel')

    def monad_redbrick_run(self):
        self.update_num_try()

        b_okx_login = False
        for i in range(1, DEF_NUM_TRY+1):
            if i >= DEF_NUM_TRY/2:
                is_bulk = True
            else:
                is_bulk = False
            b_okx_login = self.init_okx(is_bulk)
            if b_okx_login is False:
                self.logit(None, f'init_okx failed, is_bulk={is_bulk}, try_i={i}/{DEF_NUM_TRY}') # noqa
                continue
            if b_okx_login:
                break
        if b_okx_login is False:
            self.logit('monad_redbrick_run', 'okx login failed [ERROR]')
            return False

        for i in range(1, DEF_NUM_TRY+1):
            if self.monad_redbrick_login():
                break

        for i in range(1, DEF_NUM_TRY+1):
            if self.mint_game_pass():
                break

        for i in range(1, DEF_NUM_TRY+1):
            self.logit(None, f'[daily_checkin] try_i={i}/{DEF_NUM_TRY}')
            if self.daily_checkin():
                break

        self.logit('monad_redbrick_run', 'Finished!')
        self.close()

        return True


def send_msg(instMonadTask, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            lst_status = None
            if s_profile in instMonadTask.dic_status:
                lst_status = instMonadTask.dic_status[s_profile]

            if lst_status is None:
                lst_status = [s_profile, -1]

            s_info += '- {},{}\n'.format(
                s_profile,
                lst_status[IDX_NEXT_CLAIM],
            )
        d_cont = {
            'title': 'Daily Check-In Finished! [monad_redbrick]',
            'text': (
                'Daily Check-In [monad_redbrick]\n'
                '- account,time_next_claim\n'
                '{}\n'
                .format(s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    instMonadTask = MonadTask()

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(instMonadTask.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []
    lst_wait = []

    def get_sec_wait(lst_status):
        n_sec_wait = 0
        if lst_status:
            avail_time = lst_status[IDX_NEXT_CLAIM]
            if avail_time:
                n_sec_wait = time_difference(avail_time) + 1

        return n_sec_wait

    # 将已完成的剔除掉
    instMonadTask.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in instMonadTask.dic_status:
            lst_status = instMonadTask.dic_status[s_profile]
            n_sec_wait = get_sec_wait(lst_status)
            if n_sec_wait > 0:
                lst_wait.append([s_profile, n_sec_wait])
                # logger.info(f'[{s_profile}] 还需等待{n_sec_wait}秒') # noqa
                n += 1
                profiles.pop(i)
        else:
            continue
    logger.info('#'*40)
    if len(lst_wait) > 0:
        n_top = 5
        logger.info(f'***** Top {n_top} wait list')
        sorted_lst_wait = sorted(lst_wait, key=lambda x: x[1], reverse=False)
        for (s_profile, n_sec_wait) in sorted_lst_wait[:n_top]:
            logger.info(f'[{s_profile}] 还需等待{seconds_to_hms(n_sec_wait)}') # noqa
    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in instMonadTask.dic_purse:
            logger.info(f'{s_profile} is not in purse conf [ERROR]')
            sys.exit(0)

        def _run():
            s_directory = f'{DEF_PATH_USER_DATA}/{args.s_profile}'
            if os.path.exists(s_directory) and os.path.isdir(s_directory):
                pass
            else:
                # Create new profile
                # instMonadTask.initChrome(args.s_profile)
                # instMonadTask.init_okx()
                # instMonadTask.close()
                pass

            instMonadTask.initChrome(args.s_profile)
            is_claim = instMonadTask.monad_redbrick_run()
            return is_claim

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                if j > 1:
                    logger.info(f'⚠️ 正在重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                instMonadTask.set_args(args)
                instMonadTask.status_load()

                if s_profile in instMonadTask.dic_status:
                    lst_status = instMonadTask.dic_status[s_profile]
                else:
                    lst_status = None

                n_sec_wait = get_sec_wait(lst_status)
                if n_sec_wait > 0:
                    logger.info(f'[{s_profile}] Last update at {lst_status[IDX_UPDATE]}') # noqa
                    break
                else:
                    if _run():
                        lst_success.append(s_profile)
                        instMonadTask.close()
                        break

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                instMonadTask.close()
                if j < max_try_except:
                    time.sleep(5)

        if instMonadTask.is_update is False:
            continue

        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile} Finish]')

        if len(items) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    send_msg(instMonadTask, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    if args.loop_interval <= 0:
        main(args)
    else:
        while True:
            main(args)
            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
# noqa
python monad_redbrick.py --sleep_sec_min=30 --sleep_sec_max=60 --loop_interval=60
python monad_redbrick.py --sleep_sec_min=600 --sleep_sec_max=1800 --loop_interval=180
python monad_redbrick.py --sleep_sec_min=60 --sleep_sec_max=180
"""
