class StateStore:
    def __init__(self):
        self.sent_exec_ids = set()

    def should_send_exec(self, exec_id):
        if exec_id in self.sent_exec_ids:
            return False
        self.sent_exec_ids.add(exec_id)
        return True