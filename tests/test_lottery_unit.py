from brownie import Lottery, accounts, config, network, exceptions
from scripts.deploy_lottery import deploy_lottery
from web3 import Web3
import pytest
from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    fund_with_link,
    get_contract,
)


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # Arrange
    lottery = deploy_lottery()
    # Act
    entrance_fee = lottery.getEntranceFee()
    # Assert
    # 2000/1 = 50/x = 0.025
    expected_entrance_fee = Web3.toWei(50.0 / 2_000.0, "ether")
    assert entrance_fee == expected_entrance_fee


def test_cant_enter_unless_started():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    # Act / Assert
    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter(
            {
                "from": get_account(),
                "value": lottery.getEntranceFee(),
                "required_confs": 1,
            }
        )


def test_can_start_and_enter_lottery():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account, "required_confs": 1})
    # act
    lottery.enter(
        {"from": account, "required_confs": 1, "value": lottery.getEntranceFee()}
    )
    # assert
    assert lottery.players(0) == account


def test_can_end_lottery():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account, "required_confs": 1})
    lottery.enter(
        {"from": account, "value": lottery.getEntranceFee(), "required_confs": 1}
    )
    fund_with_link(lottery)
    lottery.endLottery({"from": account, "required_confs": 1})
    assert lottery.lottery_state() == 2


def test_can_pick_winner_correctly():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account, "required_confs": 1})
    lottery.enter(
        {"from": account, "value": lottery.getEntranceFee(), "required_confs": 1}
    )
    lottery.enter(
        {
            "from": get_account(index=1),
            "value": lottery.getEntranceFee(),
            "required_confs": 1,
        }
    )
    lottery.enter(
        {
            "from": get_account(index=2),
            "value": lottery.getEntranceFee(),
            "required_confs": 1,
        }
    )
    fund_with_link(lottery)
    #### he had this section after endLottery before which i think is a mistake...
    starting_balance_of_account = account.balance()
    balance_of_lottery = lottery.balance()
    ###############################################################################
    transaction = lottery.endLottery({"from": account, "required_confs": 1})
    request_id = transaction.events["RequestedRandomness"]["requestId"]
    STATIC_RNG = 777
    get_contract("vrf_coordinator").callBackWithRandomness(
        request_id, STATIC_RNG, lottery.address, {"from": account, "required_confs": 1}
    )
    # 777 % 3 = 0 (777 / 3 = 259)

    assert (
        lottery.recentWinner() == account
    )  # account is the 0th lottery entrant. Since 777 % 3 == 0, should be 0th
    assert lottery.balance() == 0
    assert account.balance() == starting_balance_of_account + balance_of_lottery
