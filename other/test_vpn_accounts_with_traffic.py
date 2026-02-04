import requests
import re
import pandas as pd
import time
import base64
import yaml
from typing import Dict, List, Optional
from loguru import logger
import os

# 配置日志
logger.add("vpn_account_with_traffic_test.log", rotation="1 day", retention="7 days", encoding="utf-8")

class ClashTrafficTester:
    """Clash X Pro 流量测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    def test_config_traffic(self, url: str) -> Dict:
        """测试Clash配置文件的剩余流量"""
        if not url:
            return {
                'success': False,
                'message': '没有提供配置文件链接',
                'traffic_info': {},
                'config_type': 'unknown'
            }
        
        try:
            # 先尝试从订阅服务器获取流量信息
            server_traffic = self._get_server_traffic_info(url)
            
            # 下载配置文件
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'配置文件下载失败，状态码: {response.status_code}',
                    'traffic_info': server_traffic if server_traffic else {},
                    'config_type': 'unknown'
                }
            
            # 检查配置文件类型
            config_content = response.text
            config_type = self._detect_config_type(config_content)
            
            if config_type == 'clash':
                # Clash 配置文件
                result = self._parse_clash_config(config_content)
            elif config_type == 'surge':
                # Surge 配置文件
                result = self._parse_surge_config(config_content)
            elif config_type == 'base64':
                # Base64 编码的配置文件
                result = self._parse_base64_config(config_content)
            elif config_type == 'v2ray':
                # V2Ray 配置文件
                result = self._parse_v2ray_config(config_content)
            else:
                # 未知类型，尝试直接解析
                result = self._parse_generic_config(config_content)
            
            # 合并服务器流量信息和配置文件流量信息
            if server_traffic:
                result['traffic_info'].update({k: v for k, v in server_traffic.items() if not result['traffic_info'].get(k)})
            
            return {
                **result,
                'success': True,
                'message': f'成功解析{config_type}类型配置文件',
                'config_type': config_type
            }
            
        except Exception as e:
            logger.error(f"测试配置文件流量时发生错误: {e}")
            return {
                'success': False,
                'message': str(e),
                'traffic_info': {},
                'config_type': 'unknown'
            }
    
    def _detect_config_type(self, content: str) -> str:
        """检测配置文件类型"""
        if not content:
            return 'unknown'
        
        content_lower = content.lower()
        
        # 检查是否为Base64编码
        if re.match(r'^[A-Za-z0-9+/]+={0,2}$', content.strip()):
            return 'base64'
        
        # 检查是否为Clash配置
        if 'proxies:' in content_lower or 'proxy-providers:' in content_lower:
            return 'clash'
        
        # 检查是否为Surge配置
        if 'proxies =' in content_lower or '[proxy]' in content_lower:
            return 'surge'
        
        # 检查是否为V2Ray配置
        if 'v2ray' in content_lower or 'vmess' in content_lower or 'trojan' in content_lower:
            return 'v2ray'
        
        # 检查是否为JSON格式
        try:
            json.loads(content)
            return 'json'
        except:
            pass
        
        # 检查是否为YAML格式
        try:
            yaml.safe_load(content)
            return 'yaml'
        except:
            pass
        
        return 'unknown'
    
    def _parse_clash_config(self, content: str) -> Dict:
        """解析Clash配置文件"""
        try:
            # 尝试解析YAML格式
            config = yaml.safe_load(content)
            
            traffic_info = {
                'total_traffic': None,
                'used_traffic': None,
                'remaining_traffic': None,
                'expire_time': None,
                'proxy_count': 0
            }
            
            # Clash X Pro 特殊处理
            if config:
                # 1. 检查proxy-providers（Clash X Pro支持的方式）
                if 'proxy-providers' in config:
                    proxy_providers = config['proxy-providers']
                    traffic_info['proxy_count'] = len(proxy_providers)
                    
                    # 检查每个provider的url是否包含流量信息
                    for name, provider in proxy_providers.items():
                        if 'url' in provider:
                            provider_url = provider['url']
                            # 从url中提取流量信息
                            url_traffic = self._extract_traffic_from_url(provider_url)
                            if url_traffic:
                                traffic_info.update(url_traffic)
                            
                            # 尝试从provider的url获取服务器流量信息
                            server_traffic = self._get_server_traffic_info(provider_url)
                            if server_traffic:
                                traffic_info.update(server_traffic)
            
            # 2. 检查proxies
            if 'proxies' in config:
                traffic_info['proxy_count'] = max(traffic_info['proxy_count'], len(config['proxies']))
            
            # 3. 检查Clash X Pro特有的信息
            # 检查mixed-port或port配置
            if config and ('mixed-port' in config or 'port' in config):
                traffic_info['clash_x_pro_supported'] = True
            
            # 4. 尝试从注释中提取流量信息
            # 搜索所有注释
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # 从注释行提取流量信息
                    comment_traffic = self._extract_traffic_from_comment(line)
                    if comment_traffic:
                        traffic_info.update(comment_traffic)
                        break
            
            # 5. 尝试从整个内容中提取流量信息
            content_traffic = self._extract_traffic_from_content(content)
            if content_traffic:
                traffic_info.update({k: v for k, v in content_traffic.items() if not traffic_info.get(k)})
            
            return {'traffic_info': traffic_info}
            
        except Exception as e:
            logger.error(f"解析Clash配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_surge_config(self, content: str) -> Dict:
        """解析Surge配置文件"""
        try:
            traffic_info = {
                'total_traffic': None,
                'used_traffic': None,
                'remaining_traffic': None,
                'expire_time': None,
                'proxy_count': 0
            }
            
            # 计数proxy数量
            proxies = re.findall(r'^[a-zA-Z0-9_-]+\s*=.*$', content, re.MULTILINE)
            traffic_info['proxy_count'] = len(proxies)
            
            # 尝试从注释中提取流量信息
            comments = re.findall(r'#.*流量.*', content)
            if comments:
                for comment in comments:
                    comment_traffic = self._extract_traffic_from_comment(comment)
                    if comment_traffic:
                        traffic_info.update(comment_traffic)
                        break
            
            return {'traffic_info': traffic_info}
            
        except Exception as e:
            logger.error(f"解析Surge配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_base64_config(self, content: str) -> Dict:
        """解析Base64编码的配置文件"""
        try:
            # 解码Base64
            decoded_content = base64.b64decode(content).decode('utf-8', errors='ignore')
            
            # 重新检测类型
            config_type = self._detect_config_type(decoded_content)
            
            if config_type == 'clash':
                return self._parse_clash_config(decoded_content)
            elif config_type == 'surge':
                return self._parse_surge_config(decoded_content)
            elif config_type == 'v2ray':
                return self._parse_v2ray_config(decoded_content)
            else:
                return self._parse_generic_config(decoded_content)
                
        except Exception as e:
            logger.error(f"解析Base64配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_v2ray_config(self, content: str) -> Dict:
        """解析V2Ray配置文件"""
        try:
            # 尝试解析JSON
            try:
                config = json.loads(content)
                traffic_info = {
                    'total_traffic': None,
                    'used_traffic': None,
                    'remaining_traffic': None,
                    'expire_time': None,
                    'proxy_count': 1
                }
            except:
                # 不是JSON格式，可能是V2RayN格式
                traffic_info = {
                    'total_traffic': None,
                    'used_traffic': None,
                    'remaining_traffic': None,
                    'expire_time': None,
                    'proxy_count': 1
                }
            
            # 尝试从内容中提取流量信息
            traffic_info.update(self._extract_traffic_from_content(content))
            
            return {'traffic_info': traffic_info}
            
        except Exception as e:
            logger.error(f"解析V2Ray配置文件失败: {e}")
            return {'traffic_info': {}}
    
    def _parse_generic_config(self, content: str) -> Dict:
        """解析通用配置文件"""
        traffic_info = {
            'total_traffic': None,
            'used_traffic': None,
            'remaining_traffic': None,
            'expire_time': None,
            'proxy_count': 0
        }
        
        # 尝试提取流量信息
        traffic_info.update(self._extract_traffic_from_content(content))
        
        return {'traffic_info': traffic_info}
    
    def _extract_traffic_from_content(self, content: str) -> Dict:
        """从配置文件内容中提取流量信息"""
        traffic_info = {}
        
        # 提取流量信息的正则表达式
        patterns = {
            'total_traffic': [
                r'总流量[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'total[:：]\s*([\d.]+\s*[TGMBK]?i?B?)'
            ],
            'used_traffic': [
                r'已用流量[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'used[:：]\s*([\d.]+\s*[TGMBK]?i?B?)'
            ],
            'remaining_traffic': [
                r'剩余流量[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'remaining[:：]\s*([\d.]+\s*[TGMBK]?i?B?)',
                r'剩余[:：]\s*([\d.]+\s*[TGMBK]?i?B?)'
            ],
            'expire_time': [
                r'到期时间[:：]\s*([^\s]+)',
                r'expire[:：]\s*([^\s]+)',
                r'有效期[:：]\s*([^\s]+)'
            ]
        }
        
        for key, key_patterns in patterns.items():
            for pattern in key_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    traffic_info[key] = match.group(1).strip()
                    break
        
        return traffic_info
    
    def _extract_traffic_from_url(self, url: str) -> Dict:
        """从URL中提取流量信息"""
        traffic_info = {}
        
        # 提取流量信息的正则表达式
        patterns = {
            'total_traffic': r'[&?](total|traffic|data)=([\d.]+[TGMBK]?i?B?)',
            'used_traffic': r'[&?]used=([\d.]+[TGMBK]?i?B?)',
            'remaining_traffic': r'[&?](remaining|left)=([\d.]+[TGMBK]?i?B?)',
            'expire_time': r'[&?]expire=([^&]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                traffic_info[key] = match.group(2) if key in ['total_traffic', 'remaining_traffic'] else match.group(1)
        
        return traffic_info
    
    def _extract_traffic_from_comment(self, comment: str) -> Dict:
        """从注释中提取流量信息"""
        return self._extract_traffic_from_content(comment)
    
    def _get_server_traffic_info(self, url: str) -> Dict:
        """从订阅服务器获取流量信息"""
        traffic_info = {}
        
        try:
            from urllib.parse import urlparse, parse_qs
            
            # 解析URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
            
            # 检查常见的订阅服务器提供商
            if 'shadowrocket.live' in domain:
                # shadowrocket.live 服务器
                traffic_info = self._get_shadowrocket_traffic(url)
            elif 'vip16888.com' in domain:
                # vip16888.com 服务器
                traffic_info = self._get_vip16888_traffic(url)
            elif 'clash1688.com' in domain:
                # clash1688.com 服务器
                traffic_info = self._get_clash1688_traffic(url)
            elif 'malls1688.top' in domain:
                # malls1688.top 服务器
                traffic_info = self._get_malls1688_traffic(url)
            else:
                # 尝试通用方法
                traffic_info = self._get_generic_server_traffic(url)
            
        except Exception as e:
            logger.debug(f"从服务器获取流量信息失败: {e}")
        
        return traffic_info
    
    def _get_shadowrocket_traffic(self, url: str) -> Dict:
        """获取 shadowrocket.live 服务器的流量信息"""
        # shadowrocket.live 通常在订阅链接中包含流量信息
        return self._extract_traffic_from_url(url)
    
    def _get_vip16888_traffic(self, url: str) -> Dict:
        """获取 vip16888.com 服务器的流量信息"""
        traffic_info = {}
        
        try:
            # 尝试从URL路径中提取用户ID
            match = re.search(r'cla/([a-f0-9-]+)', url, re.IGNORECASE)
            if match:
                user_id = match.group(1)
                # vip16888.com 的流量查询API
                api_url = f"https://www.vip16888.com/api/user/traffic?uuid={user_id}"
                response = self.session.get(api_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        traffic_info = {
                            'total_traffic': data.get('totalTraffic'),
                            'used_traffic': data.get('usedTraffic'),
                            'remaining_traffic': data.get('remainingTraffic'),
                            'expire_time': data.get('expireTime')
                        }
        except Exception as e:
            logger.debug(f"获取 vip16888.com 流量信息失败: {e}")
        
        return traffic_info
    
    def _get_clash1688_traffic(self, url: str) -> Dict:
        """获取 clash1688.com 服务器的流量信息"""
        # clash1688.com 通常在配置文件中包含流量信息
        return {}
    
    def _get_malls1688_traffic(self, url: str) -> Dict:
        """获取 malls1688.top 服务器的流量信息"""
        # malls1688.top 通常在URL中包含流量信息
        return self._extract_traffic_from_url(url)
    
    def _get_generic_server_traffic(self, url: str) -> Dict:
        """获取通用服务器的流量信息"""
        traffic_info = {}
        
        try:
            # 尝试解析常见的流量参数格式
            params = re.findall(r'([^=&]+)=([^=&]+)', url)
            param_dict = dict(params)
            
            # 检查常见的流量参数
            traffic_mapping = {
                'total': 'total_traffic',
                'used': 'used_traffic',
                'remaining': 'remaining_traffic',
                'expire': 'expire_time',
                'traffic': 'total_traffic',
                'data': 'total_traffic'
            }
            
            for param, key in traffic_mapping.items():
                if param in param_dict:
                    traffic_info[key] = param_dict[param]
            
        except Exception as e:
            logger.debug(f"获取通用服务器流量信息失败: {e}")
        
        return traffic_info

class VPNAccountTester:
    """VPN账号批量测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.traffic_tester = ClashTrafficTester()
    
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
    
    def test_account(self, account: str, password: str, config_url: str) -> Dict:
        """测试单个VPN账号的可用性和流量信息"""
        result = {
            '账号': account,
            '密码': password,
            '配置文件链接': config_url,
            '测试状态': '失败',
            '响应码': '',
            '测试信息': '',
            '平台': '',
            '配置类型': '',
            '支持Clash X Pro': '否',
            '总流量': '配置文件中未包含',
            '已用流量': '配置文件中未包含',
            '剩余流量': '配置文件中未包含',
            '到期时间': '配置文件中未包含',
            '节点数量': 0
        }
        
        try:
            # 测试配置文件URL是否可访问
            response = self.session.get(config_url, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                result['测试状态'] = '成功'
                result['响应码'] = response.status_code
                result['测试信息'] = '配置文件下载成功'
                
                # 提取平台信息
                result['平台'] = self.extract_platform_from_url(config_url)
                
                # 测试流量信息
                traffic_result = self.traffic_tester.test_config_traffic(config_url)
                
                result['配置类型'] = traffic_result['config_type']
                result['支持Clash X Pro'] = '是' if traffic_result['traffic_info'].get('clash_x_pro_supported', False) else '否'
                result['总流量'] = traffic_result['traffic_info'].get('total_traffic', '配置文件中未包含')
                result['已用流量'] = traffic_result['traffic_info'].get('used_traffic', '配置文件中未包含')
                result['剩余流量'] = traffic_result['traffic_info'].get('remaining_traffic', '配置文件中未包含')
                result['到期时间'] = traffic_result['traffic_info'].get('expire_time', '配置文件中未包含')
                result['节点数量'] = traffic_result['traffic_info'].get('proxy_count', 0)
                
                # 如果是Clash配置，添加说明
                if traffic_result['config_type'] == 'clash':
                    result['流量说明'] = 'Clash配置文件本身不包含流量信息，流量数据通常存储在服务器端，需要通过认证API获取'
                
            else:
                result['响应码'] = response.status_code
                result['测试信息'] = f'配置文件下载失败，状态码: {response.status_code}'
                
        except Exception as e:
            logger.error(f"测试账号 {account} 时发生错误: {e}")
            result['测试信息'] = str(e)
        
        return result
    
    def batch_test_accounts(self, accounts: List[Dict]) -> List[Dict]:
        """批量测试VPN账号"""
        results = []
        
        for i, account_info in enumerate(accounts):
            account = account_info.get('账号', '')
            password = account_info.get('密码', '')
            config_url = account_info.get('配置文件链接', '')
            
            logger.info(f"正在测试第 {i+1}/{len(accounts)} 个账号: {account}")
            
            # 跳过没有配置文件链接的账号
            if not config_url:
                logger.warning(f"账号 {account} 没有配置文件链接，跳过测试")
                continue
            
            # 测试账号
            result = self.test_account(account, password, config_url)
            
            # 添加原始数据
            for key, value in account_info.items():
                if key not in result:
                    result[key] = value
            
            results.append(result)
            
            # 等待一段时间避免被封禁
            time.sleep(1)
        
        return results

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
    tester = VPNAccountTester()
    
    # 批量测试账号
    logger.info(f"开始批量测试 {len(vpn_accounts)} 个VPN账号...")
    results = tester.batch_test_accounts(vpn_accounts)
    
    # 统计结果
    total_count = len(results)
    success_count = sum(1 for r in results if r['测试状态'] == '成功')
    
    logger.info(f"\n测试完成！")
    logger.info(f"总测试账号数: {total_count}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {total_count - success_count}")
    logger.info(f"成功率: {success_count/total_count*100:.2f}%")
    
    # 将结果保存到CSV文件
    df = pd.DataFrame(results)
    
    # 选择要保存的列
    columns_to_save = ['序号', '账号', '密码', '测试状态', '响应码', '平台', '配置类型', '支持Clash X Pro', 
                     '总流量', '已用流量', '剩余流量', '到期时间', '节点数量', '流量说明', 
                     '测试信息', '配置文件链接', '是否已充值', '总量', '流量剩余', '备注']
    
    # 只保留数据中存在的列
    existing_columns = [col for col in columns_to_save if col in df.columns]
    
    # 保存到CSV
    output_file = 'vpn_accounts_with_traffic_test_results.csv'
    df[existing_columns].to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"测试结果已保存到: {output_file}")
    
    # 打印详细结果
    print("\n" + "="*80)
    print("VPN账号批量测试结果汇总")
    print("="*80)
    
    for result in results:
        status = "✅" if result['测试状态'] == '成功' else "❌"
        print(f"{status} 序号: {result['序号']} | 账号: {result['账号']}")
        print(f"   平台: {result['平台']} | 配置类型: {result['配置类型']}")
        print(f"   Clash X Pro支持: {result['支持Clash X Pro']}")
        print(f"   节点数量: {result['节点数量']}")
        print(f"   流量说明: {result.get('流量说明', '无')}")
        print(f"   测试状态: {result['测试状态']} ({result['响应码']})")
        print(f"   测试信息: {result['测试信息']}")
        print(f"   配置链接: {result['配置文件链接'][:50]}...")
        print("-"*80)
    
    print("\n" + "="*80)
    print("测试说明:")
    print("1. 本测试包含VPN账号可用性和Clash X Pro流量测试")
    print("2. 支持Clash、Surge、V2Ray等多种配置格式")
    print("3. Clash配置文件本身通常不包含流量信息，流量数据存储在服务器端")
    print("4. 要获取准确的流量信息，需要使用Clash X Pro客户端或服务器提供的API")
    print("5. 测试结果已保存到CSV文件，包含完整的测试数据")
    print("="*80)

if __name__ == "__main__":
    main()
