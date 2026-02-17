import sys
import traceback
from typing import Any

from trade_engine.logging.logger import logger


class CustomException(Exception):
    def __init__(self, error_message: Exception | str, error_detail: Any):
        self.error_message = error_message
        _, _, exc_tb = error_detail.exc_info()

        if exc_tb is not None:
            self.lineno = exc_tb.tb_lineno
            self.file_name = exc_tb.tb_frame.f_code.co_filename
        else:
            tb = traceback.extract_tb(sys.exc_info()[2])
            if tb:
                self.lineno = tb[-1].lineno
                self.file_name = tb[-1].filename
            else:
                frame = sys._getframe(1)
                self.lineno = frame.f_lineno
                self.file_name = frame.f_code.co_filename

    def __str__(self) -> str:
        return (
            f"Error occurred in python script name [{self.file_name}] "
            f"line number [{self.lineno}] error message [{self.error_message}]"
        )

    def __repr__(self) -> str:
        return CustomException.__name__


if __name__ == "__main__":
    try:
        logger.info("The try block has started")
        _ = 1 / 0
    except Exception as e:
        raise CustomException(e, sys) from e
