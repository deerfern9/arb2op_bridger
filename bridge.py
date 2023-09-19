import time
import random
from web3 import Web3
from datetime import datetime
from colorama import Fore, init

from config import *
init()

colors = {
    'time': Fore.MAGENTA,
    'account_info': Fore.CYAN,
    'message': Fore.BLUE,
    'error_message': Fore.RED,
    'reset': Fore.RESET
}

web3 = Web3(Web3.HTTPProvider(arbitrum_rpc))
eth_web3 = Web3(Web3.HTTPProvider(ethereum_rpc))

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


def new_print(message_type, message, is_error=False):
    print(f'{colors["time"]}{datetime.now().strftime("%d %H:%M:%S")}{colors["account_info"]} | {message_type} |'
          f' {colors[(["message", "error_message"])[is_error]]}{message}{colors["reset"]}')


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
        while web3.from_wei(eth_web3.eth.gas_price, 'gwei') > max_gwei:
            new_print('INFO', f"Current gas fee {web3.from_wei(eth_web3.eth.gas_price, 'gwei')} gwei > {max_gwei} gwei. Waiting for 17 seconds...")
            time.sleep(17)

        try:
            account = web3.eth.account.from_key(private)
            new_print(account.address, f'Swapping ETH from Arbitrum to Optimism...')
        except Exception as e:
            new_print('INFO', f'Error: {e}', is_error=True)
            continue

        try:
            amount_to_bridge = int((get_balance(account.address) - Web3.to_wei(0.0006, 'ether')) * percent_to_bridge / 100)
            if amount_to_bridge < 0:
                new_print(account.address, 'Insufficient balance', is_error=True)
                write_to_file('insufficient_balance.txt', account.key)
                continue
            bridge_txs_hash = bridge_arbitrum_optimism(account=account, amount=amount_to_bridge)
            new_print(account.address, f'Bridge transaction hash: {bridge_txs_hash.hex()}')
            write_to_file('hashes.txt', f'{private};{account.address};{bridge_txs_hash.hex()}')
            time.sleep(random.randint(*wallets_delay))
        except Exception as e:
            new_print(account.address, f'Error: {e}', is_error=True)
            write_to_file('errors.txt', f'{private};{e}')


if __name__ == '__main__':
    main()
