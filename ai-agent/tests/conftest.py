"""Pytest configuration and fixtures."""
import pytest
import os
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test', override=True)


@pytest.fixture(scope='session')
def test_config():
    """Test configuration fixture."""
    return {
        'db_url': os.getenv('DB_URL', 'postgresql://postgres:password@localhost:5432/financemanage_test'),
        'kis_mode': 'VIRTUAL',
        'log_level': 'DEBUG'
    }


@pytest.fixture
def mock_kis_response():
    """Mock KIS API response fixture."""
    return {
        'rt_cd': '0',
        'msg_cd': 'MCA00000',
        'msg1': '정상처리 되었습니다.',
        'output': {
            'stck_frgn_ntby_amt': '10000000',
            'stck_orgn_ntby_amt': '5000000'
        }
    }


@pytest.fixture
def sample_ohlcv_response():
    """Mock OHLCV response fixture."""
    return {
        'rt_cd': '0',
        'output': [
            {
                'stck_bsop_date': '20260519',
                'stck_oprc': '70000',
                'stck_hgpr': '71000',
                'stck_lwpr': '69000',
                'stck_clpr': '70500',
                'acml_vol': '10000000'
            }
        ]
    }
