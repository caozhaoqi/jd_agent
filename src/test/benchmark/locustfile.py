from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def generate_guide(self):
        self.client.post("/api/v1/generate-guide", json={
            "jd_text": "Python 后端开发..."
        })