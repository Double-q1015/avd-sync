"""
HTML解析器模块
"""
import re
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from models.cve import CVEModel

logger = logging.getLogger(__name__)


class HTMLParser:
    """HTML解析器类"""
    
    @staticmethod
    def parse_vuln_page(html: str) -> List[Dict]:
        """
        解析漏洞列表页面
        
        Args:
            html: HTML内容
            
        Returns:
            漏洞信息列表
        """
        vuln_info_list = []
        soup = BeautifulSoup(html, 'html.parser')
        trs = soup.find_all('tr')
        
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) >= 5:
                try:
                    cve_id = tds[0].find('a').text.strip()
                    description = tds[1].text.strip()
                    cwe = tds[2].find('button').text.strip() if tds[2].find('button') else None
                    date = tds[3].text.strip()
                    score = tds[4].find('button').text.strip() if tds[4].find('button') else None
                    
                    # 验证CVE ID格式
                    if re.match(r'^CVE-\d{4}-\d{4,7}$', cve_id):
                        vuln_info = {
                            'cve_id': cve_id,
                            'description': description,
                            'cwe': cwe,
                            'date': date,
                            'score': score
                        }
                        vuln_info_list.append(vuln_info)
                    else:
                        logger.warning(f"无效的CVE ID格式: {cve_id}")
                except Exception as e:
                    logger.error(f"解析表格行时出错: {e}")
                    continue
        
        return vuln_info_list
    
    @staticmethod
    def parse_vuln_detail(cve_id: str, html: str) -> CVEModel:
        """
        解析CVE详情页面
        
        Args:
            cve_id: CVE编号
            html: HTML内容
            
        Returns:
            CVE数据模型
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取产品信息
        product = HTMLParser._extract_product(soup)
        
        # 提取标题
        title = HTMLParser._extract_title(soup)
        
        # 提取危险级别
        danger_level = HTMLParser._extract_danger_level(soup)
        
        # 提取漏洞描述
        description = HTMLParser._extract_description(soup)
        
        # 提取影响范围
        impact_range = HTMLParser._extract_impact_range(soup)
        
        # 提取安全版本
        security_versions = HTMLParser._extract_security_versions(soup)
        
        # 提取解决建议
        solution_advice = HTMLParser._extract_solution_advice(soup)
        
        # 提取参考链接
        reference_links = HTMLParser._extract_reference_links(soup)
        
        # 提取指标信息（利用情况、补丁情况、披露时间）
        metrics = HTMLParser._extract_metrics(soup)
        
        # 构建CVE模型
        return CVEModel(
            cve=cve_id,
            title=title,
            product=product,
            danger_level=danger_level,
            description=description,
            impact_range=impact_range,
            security_versions=security_versions,
            solution_advice=solution_advice,
            reference_links=reference_links,
            exploitability=metrics.get('exploitability', 'N/A'),
            package=metrics.get('package', 'N/A'),
            publish_date=metrics.get('publish_date', 'N/A'),
        )
    
    @staticmethod
    def _extract_product(soup: BeautifulSoup) -> str:
        """提取产品信息"""
        try:
            tables = soup.find_all('table', class_='table')
            if len(tables) > 1:
                table = tables[1]
                for row in table.find('tbody').find_all('tr'):
                    text = row.get_text(strip=True)
                    if text.startswith("应用"):
                        cells = row.find_all('td', class_='bg-light')
                        if len(cells) > 1:
                            return cells[1].get_text(strip=True)
        except Exception as e:
            logger.debug(f"提取产品信息失败: {e}")
        return "N/A"
    
    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        """提取标题"""
        try:
            title_elem = soup.find('span', class_='header__title__text')
            if title_elem:
                return title_elem.get_text(strip=True)
        except Exception as e:
            logger.debug(f"提取标题失败: {e}")
        return "N/A"
    
    @staticmethod
    def _extract_danger_level(soup: BeautifulSoup) -> str:
        """提取危险级别"""
        try:
            badge = soup.find('span', class_='badge btn-primary')
            if badge:
                return badge.get_text(strip=True)
        except Exception as e:
            logger.debug(f"提取危险级别失败: {e}")
        return "N/A"
    
    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        """提取漏洞描述"""
        try:
            desc_elem = soup.find('div', class_='text-detail')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                # 移除"影响范围"之后的内容
                if "影响范围" in description:
                    description = description.split("影响范围")[0]
                return description
        except Exception as e:
            logger.debug(f"提取漏洞描述失败: {e}")
        return "N/A"
    
    @staticmethod
    def _extract_impact_range(soup: BeautifulSoup) -> str:
        """提取影响范围"""
        try:
            impact_range = []
            impact_header = soup.find('div', string='影响范围')
            if impact_header:
                for div in impact_header.find_next_siblings('div'):
                    impact_range.append(div.get_text(strip=True))
            
            if impact_range:
                result = "$$".join(impact_range)
                # 移除"安全版本"之后的内容
                if "安全版本" in result:
                    result = result.split("安全版本")[0]
                return result
        except Exception as e:
            logger.debug(f"提取影响范围失败: {e}")
        return "N/A"
    
    @staticmethod
    def _extract_security_versions(soup: BeautifulSoup) -> str:
        """提取安全版本"""
        try:
            security_versions = []
            security_header = soup.find('div', string='安全版本')
            if security_header:
                for div in security_header.find_next_siblings('div'):
                    security_versions.append(div.get_text(strip=True))
            
            if security_versions:
                return "$$".join(security_versions)
        except Exception as e:
            logger.debug(f"提取安全版本失败: {e}")
        return "N/A"
    
    @staticmethod
    def _extract_solution_advice(soup: BeautifulSoup) -> Optional[str]:
        """提取解决建议"""
        try:
            solution_header = soup.find('h6', string='解决建议')
            if solution_header:
                next_div = solution_header.find_next_sibling('div')
                if next_div:
                    return next_div.get_text(strip=True)
        except Exception as e:
            logger.debug(f"提取解决建议失败: {e}")
        return None
    
    @staticmethod
    def _extract_reference_links(soup: BeautifulSoup) -> List[str]:
        """提取参考链接"""
        reference_links = []
        try:
            reference_table = soup.find('table', class_='table table-sm table-responsive')
            if reference_table:
                for row in reference_table.find_all('tr'):
                    link = row.find('a')
                    if link and link.get('href'):
                        reference_links.append(link['href'])
        except Exception as e:
            logger.debug(f"提取参考链接失败: {e}")
        return reference_links
    
    @staticmethod
    def _extract_metrics(soup: BeautifulSoup) -> Dict[str, str]:
        """提取指标信息（利用情况、补丁情况、披露时间）"""
        metrics = {
            'exploitability': 'N/A',
            'package': 'N/A',
            'publish_date': 'N/A'
        }
        
        try:
            metric_divs = soup.find_all('div', class_='metric')
            for metric in metric_divs:
                try:
                    label_elem = metric.find('p', class_='metric-label')
                    value_elem = metric.find('div', class_='metric-value')
                    
                    if label_elem and value_elem:
                        label = label_elem.get_text(strip=True)
                        value = value_elem.get_text(strip=True)
                        
                        if label == "利用情况":
                            metrics['exploitability'] = value
                        elif label == "补丁情况":
                            metrics['package'] = value
                        elif label == "披露时间":
                            metrics['publish_date'] = value
                except Exception as e:
                    logger.debug(f"提取指标项失败: {e}")
                    continue
        except Exception as e:
            logger.debug(f"提取指标信息失败: {e}")
        
        return metrics

