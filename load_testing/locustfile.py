from locust import HttpUser, task, between

class B2BUser(HttpUser):
    host = "http://localhost"
    wait_time = between(1, 3)

    @task(3)
    def browse_products(self):
        """Task 1 (Weight 3): Simulate browsing Product Catalogue"""
        self.client.get("http://localhost:8002/products", name="GET /products")

    @task(1)
    def check_inventory(self):
        """Task 2 (Weight 1): Simulate checking specific item's inventory stock"""
        self.client.get("http://localhost:8004/inventory/1", name="GET /inventory/1")

    @task(1)
    def check_order_health(self):
        """Task 3 (Weight 1): Simulate hitting Order Service health check"""
        self.client.get("http://localhost:8003/health", name="GET /health")
