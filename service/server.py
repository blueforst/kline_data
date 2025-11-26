"""
服务启动脚本
"""

import uvicorn
import argparse
import logging
from pathlib import Path

from .api import create_app

# 导出app以便测试使用
app = create_app()


def setup_logging(log_level: str = "INFO"):
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """服务启动入口"""
    parser = argparse.ArgumentParser(description='K线数据服务')
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='服务监听地址'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='服务监听端口'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='启用热重载（开发模式）'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='工作进程数量'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging(args.log_level)
    
    # 创建应用
    app = create_app(config_path=args.config)
    
    # 启动服务
    logging.info(f"启动K线数据服务...")
    logging.info(f"监听地址: {args.host}:{args.port}")
    logging.info(f"API文档: http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower(),
        workers=args.workers if not args.reload else 1
    )


if __name__ == '__main__':
    main()
