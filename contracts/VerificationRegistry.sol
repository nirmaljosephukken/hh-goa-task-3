// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VerificationRegistry {
    struct Record {
        bytes32 dataHash;
        string sourceUrl;
        uint256 timestamp;
        address submitter;
    }

    mapping(bytes32 => Record) public records;

    event RecordRegistered(
        bytes32 indexed dataHash,
        string sourceUrl,
        uint256 timestamp,
        address submitter
    );

    function register(bytes32 dataHash, string calldata sourceUrl) external {
        require(records[dataHash].timestamp == 0, "Hash already registered");

        records[dataHash] = Record({
            dataHash: dataHash,
            sourceUrl: sourceUrl,
            timestamp: block.timestamp,
            submitter: msg.sender
        });

        emit RecordRegistered(
            dataHash,
            sourceUrl,
            block.timestamp,
            msg.sender
        );
    }

    function verify(bytes32 dataHash)
        external
        view
        returns (
            bool exists,
            string memory sourceUrl,
            uint256 timestamp,
            address submitter
        )
    {
        Record memory record = records[dataHash];

        return (
            record.timestamp != 0,
            record.sourceUrl,
            record.timestamp,
            record.submitter
        );
    }
}
