"""
FastAPI服务主入口
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import logging

from .models import (
    KlineResponse, 
    IndicatorResponse, 
    MetadataResponse,
    ErrorResponse,
    SymbolListResponse
)
from .dependencies import get_kline_sdk
from sdk import KlineClient as KlineSDK
from utils.timezone import parse_datetime, format_datetime

logger = logging.getLogger(__name__)


def create_app(config_path: Optional[str] = None) -> FastAPI:
    """
    创建FastAPI应用实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        FastAPI应用实例
    """
    app = FastAPI(
        title="K线数据服务",
        description="提供K线数据查询、重采样和技术指标计算的RESTful API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 存储配置路径到app state
    app.state.config_path = config_path
    
    # 注册路由
    register_routes(app)
    
    # 注册异常处理
    register_exception_handlers(app)
    
    return app


def register_routes(app: FastAPI):
    """注册所有路由"""
    
    @app.get("/", tags=["健康检查"])
    async def health_check():
        """健康检查接口"""
        return {"status": "healthy", "service": "kline-data-service"}
    
    @app.get("/api/v1/symbols", response_model=SymbolListResponse, tags=["元数据"])
    async def list_symbols(
        exchange: Optional[str] = Query(None, description="交易所过滤"),
        sdk: KlineSDK = Depends(get_kline_sdk(app))
    ):
        """
        获取所有可用的交易对列表
        
        Args:
            exchange: 可选的交易所过滤
            
        Returns:
            交易对列表
        """
        try:
            symbols = sdk.list_symbols(exchange=exchange)
            return SymbolListResponse(
                success=True,
                data=symbols,
                total=len(symbols)
            )
        except Exception as e:
            logger.error(f"获取交易对列表失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/kline", response_model=KlineResponse, tags=["K线数据"])
    async def get_kline(
        exchange: str = Query(..., description="交易所名称"),
        symbol: str = Query(..., description="交易对"),
        interval: str = Query("1m", description="K线周期"),
        start_time: Optional[str] = Query(None, description="开始时间 ISO格式"),
        end_time: Optional[str] = Query(None, description="结束时间 ISO格式"),
        limit: Optional[int] = Query(None, description="返回条数限制"),
        sdk: KlineSDK = Depends(get_kline_sdk(app))
    ):
        """
        获取K线数据
        
        Args:
            exchange: 交易所名称 (如: binance)
            symbol: 交易对 (如: BTC/USDT)
            interval: K线周期 (如: 1m, 5m, 1h, 1d)
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回条数限制
            
        Returns:
            K线数据
        """
        try:
            # 解析时间参数
            start_dt = parse_datetime(start_time) if start_time else None
            end_dt = parse_datetime(end_time) if end_time else None
            
            # 获取K线数据
            df = sdk.get_kline(
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                start_time=start_dt,
                end_time=end_dt
            )
            
            if df.empty:
                return KlineResponse(
                    success=True,
                    data=[],
                    total=0,
                    exchange=exchange,
                    symbol=symbol,
                    interval=interval
                )
            
            # 应用limit
            if limit:
                df = df.tail(limit)
            
            # 转换为字典列表
            records = df.reset_index().to_dict('records')
            
            # 格式化时间戳为本地时区（用于显示）
            for record in records:
                if 'timestamp' in record:
                    record['timestamp'] = format_datetime(record['timestamp'], for_display=True)
            
            return KlineResponse(
                success=True,
                data=records,
                total=len(records),
                exchange=exchange,
                symbol=symbol,
                interval=interval
            )
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/indicator", response_model=IndicatorResponse, tags=["技术指标"])
    async def calculate_indicator(
        exchange: str = Query(..., description="交易所名称"),
        symbol: str = Query(..., description="交易对"),
        interval: str = Query("1m", description="K线周期"),
        indicator: str = Query(..., description="指标名称"),
        params: Optional[str] = Query(None, description="指标参数JSON字符串"),
        start_time: Optional[str] = Query(None, description="开始时间 ISO格式"),
        end_time: Optional[str] = Query(None, description="结束时间 ISO格式"),
        limit: Optional[int] = Query(None, description="返回条数限制"),
        sdk: KlineSDK = Depends(get_kline_sdk(app))
    ):
        """
        计算技术指标
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            interval: K线周期
            indicator: 指标名称 (ma, ema, bollinger, rsi, macd, kdj, atr, obv)
            params: 指标参数JSON (如: {"period": 20})
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回条数限制
            
        Returns:
            包含指标数据的K线
        """
        try:
            import json
            
            # 解析时间参数为UTC
            start_dt = parse_datetime(start_time) if start_time else None
            end_dt = parse_datetime(end_time) if end_time else None
            
            # 解析指标参数
            indicator_params = json.loads(params) if params else {}
            
            # 计算指标
            df = sdk.get_kline_with_indicator(
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                indicator=indicator,
                indicator_params=indicator_params,
                start_time=start_dt,
                end_time=end_dt
            )
            
            if df.empty:
                return IndicatorResponse(
                    success=True,
                    data=[],
                    total=0,
                    exchange=exchange,
                    symbol=symbol,
                    interval=interval,
                    indicator=indicator
                )
            
            # 应用limit
            if limit:
                df = df.tail(limit)
            
            # 转换为字典列表
            records = df.reset_index().to_dict('records')
            
            # 格式化时间戳为本地时区（用于显示）
            for record in records:
                if 'timestamp' in record:
                    record['timestamp'] = format_datetime(record['timestamp'], for_display=True)
            
            return IndicatorResponse(
                success=True,
                data=records,
                total=len(records),
                exchange=exchange,
                symbol=symbol,
                interval=interval,
                indicator=indicator
            )
            
        except Exception as e:
            logger.error(f"计算指标失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/metadata", response_model=MetadataResponse, tags=["元数据"])
    async def get_metadata(
        exchange: str = Query(..., description="交易所名称"),
        symbol: str = Query(..., description="交易对"),
        sdk: KlineSDK = Depends(get_kline_sdk(app))
    ):
        """
        获取交易对的元数据信息
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            
        Returns:
            元数据信息
        """
        try:
            metadata = sdk.get_metadata(exchange=exchange, symbol=symbol)
            
            if metadata is None:
                raise HTTPException(
                    status_code=404, 
                    detail=f"未找到 {exchange}/{symbol} 的元数据"
                )
            
            return MetadataResponse(
                success=True,
                data=metadata
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取元数据失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/download", tags=["数据下载"])
    async def download_data(
        exchange: str = Query(..., description="交易所名称"),
        symbol: str = Query(..., description="交易对"),
        start_time: Optional[str] = Query(None, description="开始时间 ISO格式"),
        end_time: Optional[str] = Query(None, description="结束时间 ISO格式"),
        sdk: KlineSDK = Depends(get_kline_sdk(app))
    ):
        """
        下载K线数据到本地
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            下载任务状态
        """
        try:
            # 解析时间参数
            start_dt = parse_datetime(start_time) if start_time else None
            end_dt = parse_datetime(end_time) if end_time else None
            
            # 执行下载
            result = sdk.download_kline(
                exchange=exchange,
                symbol=symbol,
                start_time=start_dt,
                end_time=end_dt
            )
            
            return {
                "success": True,
                "message": "数据下载完成",
                "exchange": exchange,
                "symbol": symbol,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"下载数据失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=exc.detail,
                status_code=exc.status_code
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                success=False,
                error="服务器内部错误",
                status_code=500
            ).dict()
        )


# 默认应用实例
app = create_app()
