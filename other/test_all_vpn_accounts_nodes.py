import requests
import yaml
import time
import pandas as pd
from loguru import logger
from typing import List, Dict, Tuple
import re
import os

# 配置日志
logger.add("all_vpn_accounts_nodes_test.log", rotation="1 day", retention="7 days", encoding="utf-8")

class VPNNodeTester:
    """VPN节点测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def download_config(self, config_url: str) -> str:
        """下载配置文件"""
        try:
            response = requests.get(config_url, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                logger.info(f"成功下载配置文件: {config_url}")
                return response.text
            else:
                logger.error(f"配置文件下载失败，状态码: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"下载配置文件时发生错误: {e}")
            return ""
    
    def parse_clash_config(self, config_content: str) -> List[Dict]:
        """解析Clash配置文件，提取代理节点"""
        proxies = []
        
        try:
            config = yaml.safe_load(config_content)
            
            if 'proxies' in config:
                for proxy in config['proxies']:
                    proxies.append(proxy)
            
            # 检查proxy-providers
            if 'proxy-providers' in config:
                for name, provider in config['proxy-providers'].items():
                    if 'url' in provider:
                        # 下载provider配置
                        provider_content = self.download_config(provider['url'])
                        if provider_content:
                            provider_config = yaml.safe_load(provider_content)
                            if 'proxies' in provider_config:
                                proxies.extend(provider_config['proxies'])
            
            logger.info(f"成功解析 {len(proxies)} 个代理节点")
            return proxies
            
        except Exception as e:
            logger.error(f"解析Clash配置文件失败: {e}")
            return []
    
    def extract_platform_from_url(self, url: str) -> str:
        """从URL中提取平台名称"""
        if not url:
            return '未知平台'
        
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # 移除www.前缀以统一平台名称
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception as e:
            logger.debug(f"提取平台名称失败: {e}")
            return '未知平台'
    
    def test_proxy_node(self, proxy: Dict) -> Tuple[bool, str, float]:
        """测试单个代理节点是否可用"""
        proxy_type = proxy.get('type', '')
        server = proxy.get('server', '')
        port = proxy.get('port', 0)
        name = proxy.get('name', '')
        
        if not server or not port:
            return False, '缺少服务器或端口信息', 0.0
        
        # 检查节点名称中的特殊信息
        node_name = proxy.get('name', '')
        if '到期' in node_name or '流量用完' in node_name or '失效' in node_name:
            return False, '节点已到期或流量已用完（从节点名称判断）', 0.0
        
        # 检查是否为用户中心链接
        if 'usercenter' in server or 'user/center' in server:
            return False, '这是用户中心链接，不是直接代理节点', 0.0
        
        start_time = time.time()
        
        try:
            # 对于HTTP/HTTPS代理，尝试直接测试
            if proxy_type == 'http' or proxy_type == 'https':
                return self._test_http_proxy(proxy, start_time)
            else:
                # 对于其他代理类型，只进行基本连通性测试
                return self._test_proxy_connectivity(server, port, start_time)
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"测试节点 {name} 时发生错误: {e}")
            return False, str(e), response_time
    
    def _test_http_proxy(self, proxy: Dict, start_time: float) -> Tuple[bool, str, float]:
        """测试HTTP/HTTPS代理"""
        proxy_type = proxy.get('type', 'http')
        server = proxy.get('server', '')
        port = proxy.get('port', 0)
        username = proxy.get('username', '')
        password = proxy.get('password', '')
        
        try:
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{server}:{port}"
            else:
                proxy_url = f"{proxy_type}://{server}:{port}"
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试访问简单网站
            response = self.session.get('http://www.google.com/generate_204', proxies=proxies, timeout=10)
            
            response_time = time.time() - start_time
            
            if response.status_code == 204:
                return True, f'HTTP代理测试成功，状态码: {response.status_code}', response_time
            else:
                return False, f'HTTP代理测试失败，状态码: {response.status_code}', response_time
                
        except Exception as e:
            response_time = time.time() - start_time
            return False, f'HTTP代理测试失败: {str(e)}', response_time
    
    def _test_proxy_connectivity(self, server: str, port: int, start_time: float) -> Tuple[bool, str, float]:
        """测试代理服务器的基本连通性"""
        try:
            import socket
            
            # 创建TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # 连接服务器
            sock.connect((server, port))
            sock.close()
            
            response_time = time.time() - start_time
            return True, '服务器连通性测试成功', response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            return False, f'服务器连通性测试失败: {str(e)}', response_time
    
    def test_account_nodes(self, account_info: Dict) -> List[Dict]:
        """测试单个账号的所有节点"""
        results = []
        account = account_info.get('账号', '')
        config_url = account_info.get('配置文件链接', '')
        
        if not config_url:
            logger.warning(f"账号 {account} 没有配置文件链接，跳过测试")
            return results
        
        # 下载配置文件
        config_content = self.download_config(config_url)
        if not config_content:
            logger.error(f"账号 {account} 配置文件下载失败")
            return results
        
        # 解析配置文件
        proxies = self.parse_clash_config(config_content)
        if not proxies:
            logger.error(f"账号 {account} 配置文件中没有找到代理节点")
            return results
        
        # 提取平台信息
        platform = self.extract_platform_from_url(config_url)
        
        # 测试每个节点
        for i, proxy in enumerate(proxies):
            proxy_name = proxy.get('name', f'节点{i+1}')
            proxy_type = proxy.get('type', 'unknown')
            
            logger.info(f"正在测试账号 {account} 的第 {i+1}/{len(proxies)} 个节点: {proxy_name} ({proxy_type})")
            
            success, message, response_time = self.test_proxy_node(proxy)
            
            result = {
                '账号序号': account_info.get('序号', ''),
                '账号': account,
                '平台': platform,
                '配置文件链接': config_url,
                '节点序号': i+1,
                '节点名称': proxy_name,
                '代理类型': proxy_type,
                '服务器': proxy.get('server', ''),
                '端口': proxy.get('port', 0),
                '测试结果': '成功' if success else '失败',
                '响应时间': f'{response_time:.2f}秒' if response_time > 0 else '0秒',
                '测试信息': message,
                '原账号到期时间': account_info.get('到期时间', ''),
                '原账号流量剩余': account_info.get('流量剩余', ''),
                '是否已充值': account_info.get('是否已充值', '')
            }
            
            results.append(result)
            
            # 等待一段时间避免被封禁
            time.sleep(0.3)
        
        return results
    
    def batch_test_all_accounts(self, accounts: List[Dict]) -> List[Dict]:
        """批量测试所有账号的所有节点"""
        all_results = []
        
        for i, account_info in enumerate(accounts):
            account = account_info.get('账号', '')
            logger.info(f"开始测试第 {i+1}/{len(accounts)} 个账号: {account}")
            
            account_results = self.test_account_nodes(account_info)
            all_results.extend(account_results)
            
            # 测试完一个账号后等待更长时间
            time.sleep(1)
        
        return all_results

def main():
    """主函数"""
    # VPN账号数据
    vpn_accounts = [
        {"序号": 1, "账号": "17602629614", "密码": "caozhaoqi828079", "总量": "1.2TB", "流量剩余": "300GB", "到期时间": "7月16日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://shadowrocket.live/N/E/26858fd4-2930-4b5e-a86c-614a560d477c", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 2, "账号": "1150118968@qq.com", "密码": "", "总量": "", "流量剩余": "300GB", "到期时间": "5月22日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://shadowrocket.live/N/E/e4a532c7-a2e2-47db-bbc9-058bdef04acd", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 3, "账号": "16602629614", "密码": "", "总量": "", "流量剩余": "300GB", "到期时间": "6月13日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://shadowrocket.live/N/E/F7E3E61B-FF3B-4D4B-9509-5FAC8F853AE8", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 4, "账号": "13146608677", "密码": "123456", "总量": "", "流量剩余": "300GB", "到期时间": "5月22日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://shadowrocket.live/N/E/e420b3ce-ad5a-40be-90db-277e8deb37ca", "备注.1": "", "new password": "123456", "备注.2": "已充值"},
        {"序号": 5, "账号": "13671121672", "密码": "23708000", "总量": "", "流量剩余": "300GB", "到期时间": "5月22日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://shadowrocket.live/N/E/05C7148F-F01D-495F-A7E1-74253102B854", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 6, "账号": "18526062979", "密码": "", "总量": "", "流量剩余": "300GB", "到期时间": "5月19日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://www.malls1688.top/N/E/7fe48b63-f263-4343-817f-5848dfde4fbd", "备注.1": "专线", "new password": "", "备注.2": "已充值"},
        {"序号": 7, "账号": "q128zJHekn", "密码": "UP6XX8LL7L", "总量": "", "流量剩余": "300GB", "到期时间": "10月1日", "备注": "", "是否已充值": "已充值", "配置文件链接": "http://www.clash1688.com/N/E/4e090eba-25ad-4ab9-be3a-0140455b1404", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 21, "账号": "guoyuhang@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/4a8b8bab-dcf3-42c9-b7df-0bad9f86062a", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 22, "账号": "wangyuqi@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/bb56797e-e5d9-4117-8e84-dee997968e8b", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 23, "账号": "cuimanliu@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/4100c34a-247b-412c-8919-9c86e080ba36", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 24, "账号": "caozhaoqi@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/94b6559e-a616-467e-a4f6-b1d6a74a5d92", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 25, "账号": "xuyang@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/673cab8b-5232-4ae3-a3f8-d66d52506403", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 26, "账号": "lihuijie@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/f8960349-be61-46ff-99c6-a707473eb966", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 27, "账号": "liujiayi@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/dda0b3b3-1489-4a21-8e6f-e345283813d8", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 28, "账号": "haojie@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/0257967f-018d-42ae-ade7-ffd2b7a8a1ad", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 29, "账号": "changyunhao@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/6cc3c130-abd9-4d3c-a724-5976aa812d64", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 30, "账号": "wangchen@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/9b933524-857f-4b95-9125-da23716a72f9", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 31, "账号": "wangdan@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/72b25071-8fa4-4751-9b0f-5e9e63697fd7", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 32, "账号": "liuyali@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/b2b1d892-14d4-48e7-a99e-1e19b130c0bd", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 33, "账号": "chenhaiyan@zhongguangxx.cn", "密码": "23708000", "总量": "300GB", "流量剩余": "300GB", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/cla/d64f6daa-0bb3-476a-af8f-2b3ef3044777", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 34, "账号": "lihan@zhongguangxx.cn", "密码": "23708000", "总量": "", "流量剩余": "", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/usercenter/user/center.html", "备注.1": "", "new password": "", "备注.2": ""},
        {"序号": 35, "账号": "chengtianhao@zhongguangxx.cn", "密码": "23708000", "总量": "", "流量剩余": "", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/usercenter/user/center.html", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 36, "账号": "liushitong@zhongguangxx.cn", "密码": "23708000", "总量": "", "流量剩余": "", "到期时间": "", "备注": "已充值", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/usercenter/user/center.html", "备注.1": "", "new password": "", "备注.2": "已充值"},
        {"序号": 37, "账号": "zhaokexin@zhongguangxx.cn", "密码": "23708000", "总量": "", "流量剩余": "", "到期时间": "", "备注": "", "是否已充值": "", "配置文件链接": "https://www.vip16888.com/usercenter/user/center.html", "备注.1": "", "new password": "", "备注.2": "已充值"}
    ]
    
    # 创建测试器
    tester = VPNNodeTester()
    
    # 批量测试所有账号的所有节点
    logger.info(f"开始批量测试 {len(vpn_accounts)} 个VPN账号的所有节点...")
    all_results = tester.batch_test_all_accounts(vpn_accounts)
    
    # 统计结果
    total_nodes = len(all_results)
    if total_nodes > 0:
        success_nodes = sum(1 for r in all_results if r['测试结果'] == '成功')
        success_rate = success_nodes / total_nodes * 100
    else:
        success_nodes = 0
        success_rate = 0.0
    
    logger.info(f"\n测试完成！")
    logger.info(f"总测试节点数: {total_nodes}")
    logger.info(f"成功: {success_nodes}")
    logger.info(f"失败: {total_nodes - success_nodes}")
    logger.info(f"成功率: {success_rate:.2f}%")
    
    # 按账号汇总结果
    if all_results:
        df = pd.DataFrame(all_results)
        
        # 保存所有节点的详细测试结果
        detailed_output_file = 'all_vpn_nodes_detailed_test_results.csv'
        df.to_csv(detailed_output_file, index=False, encoding='utf-8-sig')
        logger.info(f"详细测试结果已保存到: {detailed_output_file}")
        
        # 按账号汇总统计
        account_summary = df.groupby(['账号序号', '账号', '平台', '配置文件链接']).agg({
            '节点序号': 'count',
            '测试结果': lambda x: (x == '成功').sum()
        }).reset_index()
        
        account_summary = account_summary.rename(columns={
            '节点序号': '节点总数',
            '测试结果': '成功节点数'
        })
        
        account_summary['成功率'] = account_summary.apply(lambda x: f"{x['成功节点数']/x['节点总数']*100:.2f}%" if x['节点总数'] > 0 else '0%', axis=1)
        
        # 添加原账号信息
        account_summary = account_summary.merge(
            pd.DataFrame(vpn_accounts)[['序号', '到期时间', '流量剩余', '是否已充值']],
            left_on='账号序号',
            right_on='序号',
            how='left'
        )
        
        account_summary = account_summary.drop('序号', axis=1)
        
        # 保存账号汇总结果
        summary_output_file = 'all_vpn_accounts_nodes_summary.csv'
        account_summary.to_csv(summary_output_file, index=False, encoding='utf-8-sig')
        logger.info(f"账号汇总结果已保存到: {summary_output_file}")
        
        # 打印账号汇总结果
        print("\n" + "="*100)
        print("VPN账号节点测试汇总结果")
        print("="*100)
        
        for _, row in account_summary.iterrows():
            status = "✅" if row['成功率'] != '0%' else "❌"
            print(f"{status} 账号: {row['账号']} | 序号: {row['账号序号']}")
            print(f"   平台: {row['平台']} | 节点总数: {row['节点总数']} | 成功节点数: {row['成功节点数']} | 成功率: {row['成功率']}")
            print(f"   原到期时间: {row['到期时间']} | 原流量剩余: {row['流量剩余']} | 是否已充值: {row['是否已充值']}")
            print(f"   配置链接: {row['配置文件链接'][:60]}...")
            print("-"*100)
        
        # 打印总体统计
        print("\n" + "="*100)
        print("总体测试统计")
        print("="*100)
        print(f"总测试账号数: {len(vpn_accounts)}")
        print(f"总测试节点数: {total_nodes}")
        print(f"总成功节点数: {success_nodes}")
        print(f"总成功率: {success_rate:.2f}%")
        print("="*100)
        
        # 打印失败原因分析
        if all_results:
            failure_reasons = df[df['测试结果'] == '失败']['测试信息'].value_counts()
            print("\n" + "="*100)
            print("失败原因分析")
            print("="*100)
            for reason, count in failure_reasons.items():
                print(f"{count}个节点: {reason}")
            print("="*100)

if __name__ == "__main__":
    main()
