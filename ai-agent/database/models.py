"""SQLAlchemy models for AI Agent database tables."""
from sqlalchemy import Column, String, Date, BigInteger, Numeric, Boolean, Integer, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from config import settings

Base = declarative_base()


class StockFilterScore(Base):
    """Stage 1 output: Stock filtering scores and selection results."""

    __tablename__ = 'stock_filter_score'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), nullable=False)
    score_date = Column(Date, nullable=False)
    foreign_net_buy = Column(BigInteger, nullable=False)
    institutional_net_buy = Column(BigInteger, nullable=False)
    vol_avg_multiple = Column(Numeric(10, 2), nullable=False)
    price_volatility = Column(Numeric(10, 4), nullable=False)
    scaler_score = Column(Numeric(10, 4), nullable=False)
    is_selected = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    morning_return = Column(Numeric(10, 4), nullable=True)  # Stage 2-1 quantitative feature
    close_position = Column(Numeric(5, 4), nullable=True)  # Stage 2-1 quantitative feature

    def __repr__(self):
        return f"<StockFilterScore({self.stock_code}, {self.score_date}, score={self.scaler_score})>"


class MarketDailySummary(Base):
    """KOSPI index and market summary data for web display."""

    __tablename__ = 'market_daily_summary'

    trade_date = Column(Date, primary_key=True)
    kospi_index = Column(Numeric(10, 2), nullable=False)
    kospi_change_rate = Column(Numeric(8, 4), nullable=False)
    kospi_volume = Column(BigInteger, nullable=False)
    kospi_trade_value = Column(BigInteger, nullable=False)  # in million KRW
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<MarketDailySummary({self.trade_date}, KOSPI={self.kospi_index})>"


class ProphetForecast(Base):
    """Prophet forecast detailed results for web display."""

    __tablename__ = 'prophet_forecast'

    stock_code = Column(String(10), primary_key=True)
    stock_name = Column(String(50), nullable=True)
    forecast_date = Column(Date, primary_key=True)  # Fixed: trade_date -> forecast_date to match DB schema

    # Detailed predictions (D+1 to D+5) - matches actual DB schema
    yhat_d1 = Column(Numeric(10, 2), nullable=True)
    yhat_d2 = Column(Numeric(10, 2), nullable=True)
    yhat_d3 = Column(Numeric(10, 2), nullable=True)
    yhat_d4 = Column(Numeric(10, 2), nullable=True)
    yhat_d5 = Column(Numeric(10, 2), nullable=True)

    yhat_upper_d1 = Column(Numeric(10, 2), nullable=True)
    yhat_upper_d2 = Column(Numeric(10, 2), nullable=True)
    yhat_upper_d3 = Column(Numeric(10, 2), nullable=True)
    yhat_upper_d4 = Column(Numeric(10, 2), nullable=True)
    yhat_upper_d5 = Column(Numeric(10, 2), nullable=True)

    yhat_lower_d1 = Column(Numeric(10, 2), nullable=True)
    yhat_lower_d2 = Column(Numeric(10, 2), nullable=True)
    yhat_lower_d3 = Column(Numeric(10, 2), nullable=True)
    yhat_lower_d4 = Column(Numeric(10, 2), nullable=True)
    yhat_lower_d5 = Column(Numeric(10, 2), nullable=True)

    # Aggregated trend features (for Gemini AI) - matches actual DB schema
    price_trend = Column(Numeric(12, 6), nullable=True)
    volume_trend = Column(Numeric(12, 6), nullable=True)
    price_uncertainty = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<ProphetForecast({self.stock_code}, {self.forecast_date}, trend={self.price_trend})>"


# Database engine and session factory
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session (dependency injection pattern)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
