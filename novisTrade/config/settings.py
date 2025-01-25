from pathlib import Path
import yaml

class Settings:
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent.parent
        self._load_config()
        
    def _load_config(self):
        # 基礎配置
        self.DEFAULT_CONFIG = {
            "api": {
                "host": "localhost",
                "port": 8000,
                "timeout": 30
            },
            "dataStream": {
                "host": "localhost",
                "port": 8765,
                "redis": {
                    "host": "localhost",
                    "port": 6379
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
        
        # 讀取自定義配置
        config_path = self.BASE_DIR / "config" / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                custom_config = yaml.safe_load(f)
                self._update_config(custom_config)
                
    def _update_config(self, custom_config):
        """遞迴更新配置"""
        def update_dict(base, update):
            for key, value in update.items():
                if isinstance(value, dict) and key in base:
                    update_dict(base[key], value)
                else:
                    base[key] = value
                    
        update_dict(self.DEFAULT_CONFIG, custom_config)

settings = Settings()