import requests
import re
import json
import pandas as pd
import time
from typing import Dict, List, Optional
from loguru import logger

# 配置日志
logger.add("vpn_test.log", rotation="1 day", retention="7 days", encoding="utf-8")

class VPNAccountTester:
    """VPN账号测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def test_account(self, account_data: Dict) -> Dict:
        """测试单个VPN账号"""
        logger.info(f"正在测试账号: {account_data['账号']}")
        
        # 提取平台信息
        platform = self._extract_platform(account_data['配置文件链接'])
        
        try:
            # 根据不同平台选择测试方法
            if platform == 'shadowrocket.live':
                result = self._test_shadowrocket_platform(account_data)
            elif platform == 'malls1688.top':
                result = self._test_malls_platform(account_data)
            elif platform == 'clash1688.com':
                result = self._test_clash_platform(account_data)
            elif platform == 'vip16888.com':
                result = self._test_vip_platform(account_data)
            else:
                result = {
                    'success': False,
                    'message': f'未知平台: {platform}',
                    'response_code': None
                }
        except Exception as e:
            logger.error(f"测试账号 {account_data['账号']} 时发生错误: {e}")
            result = {
                'success': False,
                'message': str(e),
                'response_code': None
            }
        
        # 等待一段时间避免被封禁
        time.sleep(1)
        
        return {
            **account_data,
            '测试结果': '成功' if result['success'] else '失败',
            '测试信息': result['message'],
            '响应代码': result['response_code'],
            '平台': platform
        }
    
    def _extract_platform(self, url: str) -> str:
        """从URL中提取平台信息"""
        if not url:
            return '未知'
        
        # 提取域名部分
        match = re.search(r'https?://([^/]+)', url)
        if match:
            domain = match.group(1)
            # 移除www.前缀以统一平台名称
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        
        return '未知'
    
    def _test_shadowrocket_platform(self, account_data: Dict) -> Dict:
        """测试shadowrocket.live平台"""
        url = account_data['配置文件链接']
        if not url:
            return {'success': False, 'message': '没有提供配置文件链接', 'response_code': None}
        
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # 检查响应内容是否包含配置信息
                if 'proxies' in response.text or 'Proxy' in response.text or response.text.strip().startswith('v2ray'):
                    return {
                        'success': True,
                        'message': '配置文件获取成功',
                        'response_code': response.status_code
                    }
                else:
                    return {
                        'success': False,
                        'message': '配置文件内容无效',
                        'response_code': response.status_code
                    }
            else:
                return {
                    'success': False,
                    'message': f'HTTP状态码错误: {response.status_code}',
                    'response_code': response.status_code
                }
        except requests.RequestException as e:
            return {
                'success': False,
                'message': f'请求失败: {e}',
                'response_code': None
            }
    
    def _test_malls_platform(self, account_data: Dict) -> Dict:
        """测试malls1688.top平台"""  
        return self._test_shadowrocket_platform(account_data)
    
    def _test_clash_platform(self, account_data: Dict) -> Dict:
        """测试clash1688.com平台"""
        return self._test_shadowrocket_platform(account_data)
    
    def _test_vip_platform(self, account_data: Dict) -> Dict:
        """测试vip16888.com平台"""
        url = account_data['配置文件链接']
        if not url:
            return {'success': False, 'message': '没有提供配置文件链接', 'response_code': None}
        
        # 对于usercenter链接，我们无法直接测试配置文件
        if 'usercenter' in url:
            return {
                'success': True,
                'message': '用户中心链接，无法直接测试配置文件',
                'response_code': None
            }
        
        # 对于配置文件链接，使用通用测试方法
        return self._test_shadowrocket_platform(account_data)
    
    def test_all_accounts(self, accounts_data: List[Dict]) -> List[Dict]:
        """测试所有VPN账号"""
        results = []
        
        for account_data in accounts_data:
            result = self.test_account(account_data)
            results.append(result)
            
            # 打印测试结果
            status = "✅" if result['测试结果'] == '成功' else "❌"
            logger.info(f"{status} 账号: {account_data['账号']} - {result['测试结果']}: {result['测试信息']}")
        
        return results

def main():
    """主函数"""
    # 解析用户提供的表格数据
    accounts_data = [
        {
            '序号': 1,
            '账号': '17602629614',
            '密码': 'caozhaoqi828079',
            '总量': '1.2TB',
            '流量剩余': '300GB',
            '到期时间': '7月16日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://shadowrocket.live/N/E/26858fd4-2930-4b5e-a86c-614a560d477c',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 2,
            '账号': '1150118968@qq.com',
            '密码': '',
            '总量': '',
            '流量剩余': '300GB',
            '到期时间': '5月22日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://shadowrocket.live/N/E/e4a532c7-a2e2-47db-bbc9-058bdef04acd',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 3,
            '账号': '16602629614',
            '密码': '',
            '总量': '',
            '流量剩余': '300GB',
            '到期时间': '6月13日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://shadowrocket.live/N/E/F7E3E61B-FF3B-4D4B-9509-5FAC8F853AE8',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 4,
            '账号': '13146608677',
            '密码': '123456',
            '总量': '',
            '流量剩余': '300GB',
            '到期时间': '5月22日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://shadowrocket.live/N/E/e420b3ce-ad5a-40be-90db-277e8deb37ca',
            '备注2': '',
            'new password': '123456',
            '备注3': '已充值'
        },
        {
            '序号': 5,
            '账号': '13671121672',
            '密码': '23708000',
            '总量': '',
            '流量剩余': '300GB',
            '到期时间': '5月22日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://shadowrocket.live/N/E/05C7148F-F01D-495F-A7E1-74253102B854',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 6,
            '账号': '18526062979',
            '密码': '',
            '总量': '',
            '流量剩余': '300GB',
            '到期时间': '5月19日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://www.malls1688.top/N/E/7fe48b63-f263-4343-817f-5848dfde4fbd',
            '备注2': '专线',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 7,
            '账号': 'q128zJHekn',
            '密码': 'UP6XX8LL7L',
            '总量': '',
            '流量剩余': '300GB',
            '到期时间': '10月1日',
            '备注': '',
            '是否已充值': '已充值',
            '配置文件链接': 'http://www.clash1688.com/N/E/4e090eba-25ad-4ab9-be3a-0140455b1404',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 21,
            '账号': 'guoyuhang@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/4a8b8bab-dcf3-42c9-b7df-0bad9f86062a',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 22,
            '账号': 'wangyuqi@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/bb56797e-e5d9-4117-8e84-dee997968e8b',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 23,
            '账号': 'cuimanliu@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/4100c34a-247b-412c-8919-9c86e080ba36',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 24,
            '账号': 'caozhaoqi@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/94b6559e-a616-467e-a4f6-b1d6a74a5d92',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 25,
            '账号': 'xuyang@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/673cab8b-5232-4ae3-a3f8-d66d52506403',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 26,
            '账号': 'lihuijie@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/f8960349-be61-46ff-99c6-a707473eb966',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 27,
            '账号': 'liujiayi@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/dda0b3b3-1489-4a21-8e6f-e345283813d8',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 28,
            '账号': 'haojie@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/0257967f-018d-42ae-ade7-ffd2b7a8a1ad',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 29,
            '账号': 'changyunhao@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/6cc3c130-abd9-4d3c-a724-5976aa812d64',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 30,
            '账号': 'wangchen@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/9b933524-857f-4b95-9125-da23716a72f9',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 31,
            '账号': 'wangdan@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/72b25071-8fa4-4751-9b0f-5e9e63697fd7',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 32,
            '账号': 'liuyali@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/b2b1d892-14d4-48e7-a99e-1e19b130c0bd',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 33,
            '账号': 'chenhaiyan@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '300GB',
            '流量剩余': '300GB',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/cla/d64f6daa-0bb3-476a-af8f-2b3ef3044777',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 34,
            '账号': 'lihan@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '',
            '流量剩余': '',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/usercenter/user/center.html',
            '备注2': '',
            'new password': '',
            '备注3': ''
        },
        {
            '序号': 35,
            '账号': 'chengtianhao@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '',
            '流量剩余': '',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/usercenter/user/center.html',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 36,
            '账号': 'liushitong@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '',
            '流量剩余': '',
            '到期时间': '',
            '备注': '已充值',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/usercenter/user/center.html',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        },
        {
            '序号': 37,
            '账号': 'zhaokexin@zhongguangxx.cn',
            '密码': '23708000',
            '总量': '',
            '流量剩余': '',
            '到期时间': '',
            '备注': '',
            '是否已充值': '',
            '配置文件链接': 'https://www.vip16888.com/usercenter/user/center.html',
            '备注2': '',
            'new password': '',
            '备注3': '已充值'
        }
    ]
    
    # 创建测试器
    tester = VPNAccountTester()
    
    # 批量测试所有账号
    logger.info(f"开始批量测试 {len(accounts_data)} 个VPN账号...")
    results = tester.test_all_accounts(accounts_data)
    
    # 统计结果
    success_count = sum(1 for r in results if r['测试结果'] == '成功')
    total_count = len(results)
    
    logger.info(f"\n测试完成！")
    logger.info(f"总测试账号数: {total_count}")
    logger.info(f"成功账号数: {success_count}")
    logger.info(f"失败账号数: {total_count - success_count}")
    logger.info(f"成功率: {success_count/total_count*100:.2f}%")
    
    # 将结果保存到CSV文件
    df = pd.DataFrame(results)
    
    # 选择需要保存的列
    columns_to_save = [
        '序号', '账号', '平台', '测试结果', '测试信息', '响应代码', 
        '流量剩余', '到期时间', '是否已充值', '配置文件链接'
    ]
    
    # 保存到CSV
    output_file = 'vpn_account_test_results.csv'
    df[columns_to_save].to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"测试结果已保存到: {output_file}")
    
    # 打印详细结果
    print("\n" + "="*80)
    print("VPN账号测试结果汇总")
    print("="*80)
    
    for result in results:
        status = "✅" if result['测试结果'] == '成功' else "❌"
        print(f"{status} 序号: {result['序号']} | 账号: {result['账号']} | 平台: {result['平台']} | 结果: {result['测试结果']}")
        print(f"   信息: {result['测试信息']}")
        print(f"   流量剩余: {result['流量剩余']} | 到期时间: {result['到期时间']}")
        print(f"   配置链接: {result['配置文件链接'][:50]}...")
        print("-"*80)

if __name__ == "__main__":
    main()
