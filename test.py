import time
from mcp_server.services.product_service import get_stock

s = time.time()
print(get_stock("P01230008095"))
e = time.time()

print(f"{e - s} s")

