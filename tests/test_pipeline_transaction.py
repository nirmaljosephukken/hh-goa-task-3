from src.pipeline import _registration_transaction_hash


class _Hash:
    def __init__(self, value: str):
        self._value = value

    def hex(self) -> str:
        return self._value


class _Eth:
    block_number = 12_345

    def get_logs(self, query):
        self.query = query
        return [{"transactionHash": _Hash("abc123")}]


class _Web3:
    def __init__(self):
        self.eth = _Eth()

    @staticmethod
    def keccak(*, text: str):
        assert text == "RecordRegistered(bytes32,string,uint256,address)"
        return _Hash("event-topic")


def test_existing_record_uses_registration_transaction_event():
    web3 = _Web3()
    digest = "ab" * 32

    transaction_hash = _registration_transaction_hash(web3, "0xcontract", digest)

    assert transaction_hash == "abc123"
    assert web3.eth.query["fromBlock"] == 2_346
    assert web3.eth.query["topics"] == ["0xevent-topic", f"0x{digest}"]
