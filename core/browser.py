"""
浏览器管理模块
"""
import logging
from typing import Optional
from DrissionPage import ChromiumPage, ChromiumOptions
from config.settings import BROWSER_CONFIG

logger = logging.getLogger(__name__)


class BrowserManager:
    """浏览器管理器，负责创建和管理浏览器实例"""
    
    def __init__(self):
        """初始化浏览器配置"""
        self.options = self._create_options()
        self.page: Optional[ChromiumPage] = None
    
    def _create_options(self) -> ChromiumOptions:
        """创建浏览器选项"""
        co = ChromiumOptions()
        
        # Docker环境必须的选项
        if BROWSER_CONFIG['no_sandbox']:
            co = co.set_argument('--no-sandbox')
            co = co.set_argument('--disable-setuid-sandbox')
        
        if BROWSER_CONFIG['headless']:
            # 新版本写法（使用 headless=new 兼容新版本 Chromium）
            co.headless(True)
            # 显式添加 --headless=new 参数（新版本 Chromium 推荐）
            co = co.set_argument('--headless=new')
            co = co.set_argument('--disable-gpu')  # Docker中不需要GPU
        
        # 性能优化选项
        try:
            # 禁用图片加载（减少内存和网络使用）
            co = co.set_argument('--blink-settings=imagesEnabled=false')
        except:
            pass
        
        try:
            # 禁用插件
            co = co.set_argument('--disable-plugins')
        except:
            pass
        
        # Docker环境优化选项
        try:
            # 禁用DevTools
            co = co.set_argument('--disable-dev-shm-usage')  # 使用/tmp而不是/dev/shm
            # 禁用后台网络
            co = co.set_argument('--disable-background-networking')
            # 禁用同步
            co = co.set_argument('--disable-sync')
            # 禁用默认浏览器检查
            co = co.set_argument('--no-default-browser-check')
            # 禁用扩展
            co = co.set_argument('--disable-extensions')
        except:
            pass
        
        # 注意：保留JavaScript，因为现代网站需要JS来渲染内容
        
        if BROWSER_CONFIG.get('user_agent'):
            co = co.set_user_agent(BROWSER_CONFIG['user_agent'])
        
        return co
    
    def get_page(self, reuse: bool = True) -> ChromiumPage:
        """
        获取浏览器页面实例
        
        Args:
            reuse: 是否复用现有页面
            
        Returns:
            ChromiumPage实例
        """
        if reuse and self.page is not None:
            return self.page
        
        self.page = ChromiumPage(self.options)
        logger.debug("创建新的浏览器页面实例")
        return self.page
    
    def close(self):
        """关闭浏览器"""
        if self.page is not None:
            try:
                self.page.quit()  # 使用 quit() 完全关闭浏览器进程，避免残留
                logger.debug("浏览器已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器时出错: {e}")
            finally:
                self.page = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

