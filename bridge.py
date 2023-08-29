import random
import time
from web3 import Web3
from datetime import datetime

from config import *

web3 = Web3(Web3.HTTPProvider(arbitrum_rpc_url))

stargate_router_contract = web3.eth.contract(
    address=web3.to_checksum_address(stargate_arbitrum_address),
    abi=router_abi
)
stargate_router_eth_contract = web3.eth.contract(
    address=web3.to_checksum_address(stargate_arbitrum_eth_address),
    abi=router_eth_abi
)


def read_file(filename):
    result = []
    with open(filename, 'r') as file:
        for tmp in file.readlines():
            result.append(tmp.strip())

    return result


def write_to_file(filename, text):
    with open(filename, 'a') as file:
        file.write(f'{text}\n')


def get_balance(address):
    return web3.eth.get_balance(address)


def bridge_arbitrum_optimism(account, amount):
    address = account.address
    nonce = web3.eth.get_transaction_count(address)
    gas_price = web3.eth.gas_price
    fees = stargate_router_contract.functions.quoteLayerZeroFee(
        111,
        1,
        address,
        "0x",
        [0, 0, address]
    ).call()
    fee = fees[0]

    amount_out_min = amount - (amount * SLIPPAGE) // 1000
    print(amount, amount_out_min)
    swap_txn = stargate_router_eth_contract.functions.swapETH(
        111, address, address, amount, amount_out_min
    ).build_transaction({
        'from': address,
        'value': amount + fee,
        'gasPrice': gas_price,
        'nonce': nonce,
    })

    signed_swap_txn = web3.eth.account.sign_transaction(swap_txn, account.key)
    swap_txn_hash = web3.eth.send_raw_transaction(signed_swap_txn.rawTransaction)
    return swap_txn_hash


def main():
    privates = read_file('privates.txt')
    for private in privates:
        account = web3.eth.account.from_key(private)
        print(f'{datetime.now().strftime("%d %H:%M:%S")} | {account.address} | '
              f'Swapping ETH from Arbitrum to Optimism...')
        try:
            amount_to_bridge = int((get_balance(account.address) - Web3.to_wei(0.0008, 'ether')) * percent_to_bridge / 100)
            bridge_txs_hash = bridge_arbitrum_optimism(account=account, amount=amount_to_bridge)
            print(f'{datetime.now().strftime("%d %H:%M:%S")} | {account.address} | Bridge transaction hash: '
                  f'{bridge_txs_hash.hex()}')
            write_to_file('hashes.txt', f'{private};{account.address};{bridge_txs_hash.hex()}')
            time.sleep(random.randint(*wallets_delay))
        except Exception as e:
            print(f'{datetime.now().strftime("%d %H:%M:%S")} | {account.address} | {e}')
            write_to_file('errors.txt', f'{private};{e}')


if __name__ == '__main__':
    main()
