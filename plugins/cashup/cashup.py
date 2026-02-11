# importing nio-stuff
from core.plugin import Plugin
from core.bot_commands import Command
# from nio import AsyncClient, RoomMessageText
# from nio.responses import RoomContextResponse, RoomContextError

import logging

# importing cash up stuff
# import functools  # for reduce()

# importing regular expressions for parsing numbers
import re
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)
plugin = Plugin("cashup", "General", "A very simple cashup plugin to share expenses in a group")


ROOM_DB_TYPE = dict  # [str, any]
ROOMS_DB_TYPE = dict[str, ROOM_DB_TYPE] | None  # None if no data saved before
# find any numbers in string (eg: 12; 12,1; 12.1)
RE_MATCH_EXPENSE_NR = r'\d*[.,]?\d+'


def setup():
    # first command will be called when plugin name is called
    plugin.add_command(
        "cashup-register",
        register,
        "Resets existing expenses and initializes all group members for sharing expenses.",
        power_level=100,
    )
    plugin.add_command(
        "cashup-add-expense",
        add_expense_for_user,
        "Adds a new expense for the given user-name.",
    )
    plugin.add_command(
        "cashup-rm-expense",
        rm_expense_for_user,
        "Removes the last expense added for the given user-name.",
    )
    plugin.add_command(
        "cashup-add-loan",
        add_loan,
        "Adds a new loan for a given user-name to an other user-name.",
    )
    plugin.add_command(
        "cashup-rm-loan",
        rm_loan,
        "Removes the last loan added for a given user-name to an other user-name.",
    )
    plugin.add_command("cashup-print", print_room_state, "debug print function")
    plugin.add_command(
        "cashup",
        cash_up,
        "Settle all recorded expenses among the previously registered group.",
        power_level=50,
    )
    plugin.add_command("cashup-ae", add_expense_for_user, "Short form for `cashup-add-expense`")
    plugin.add_command("cashup-al", add_loan, "Short form for `cashup-add-loan`",
    )
    plugin.add_command("cashup-p", print_room_state, "Short form for `cashup-print`")

    plugin.add_command("chasup-set-currency-sign", set_currency_sign,
                       "Set a currency sign for a previously registered group in this room. "
                       "By default currency_sign from cashup.yaml will be used")

    """Defining a configuration values to be expected in the plugin's configuration file and reading the value
    Defines a currency_sign used for a nice output message
    """
    plugin.add_config("currency_sign", "€", is_required=True)


# plugin helpers?
# read_room_db_from_command
async def get_room_db_from_command(command: Command) -> ROOM_DB_TYPE:
    return await get_room_db_from_room_id(command.room.room_id)


# plugin helpers?
# read_room_db_from_room_id
async def get_room_db_from_room_id(room_id: str) -> ROOM_DB_TYPE:
    rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
    try:
        return rooms_db[room_id]
    except (KeyError, TypeError):
        logger.debug(f"No room db found for {room_id}")
        return {}


# plugin helpers?
# store_room_db_from_command
async def save_room_db_from_command(command: Command, room_db: ROOM_DB_TYPE) -> bool:
    return await save_room_db_from_room_id(command.room.room_id, room_db)


async def save_room_db_from_room_id(room_id: str, room_db: ROOM_DB_TYPE) -> bool:
    rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
    if rooms_db is None:
        rooms_db = {}
    rooms_db[room_id] = room_db
    return await plugin.store_data("rooms_db", rooms_db)


# plugin helpers?
# store_room_db_from_db
async def update_room_db_from_command(command: Command, update_db: ROOM_DB_TYPE) -> bool:
    return await update_room_db_from_room_id(command.room.room_id, update_db)


async def update_room_db_from_room_id(room_id: str, update_db: ROOM_DB_TYPE) -> bool:
    room_db: ROOM_DB_TYPE = await get_room_db_from_room_id(room_id)
    room_db.update(update_db)
    return await save_room_db_from_room_id(room_id, room_db)


# plugin helpers?
async def clear_room_db_from_command(command: Command) -> bool:
    return await clear_room_db_from_room_id(command.room.room_id)


async def clear_room_db_from_room_id(room_id: str) -> bool:
    rooms_db: ROOMS_DB_TYPE = await plugin.read_data("rooms_db")
    del rooms_db[room_id]
    return await plugin.store_data("rooms_db", rooms_db)


def print_currency(value: float, currency_sign: str):
    clean_currency: str = "{:.2f}".format(value)
    clean_currency += currency_sign
    return clean_currency


def find_currency(command: Command) -> (int | None, float | None):
    idx = None
    currency_number = None
    for i, arg in enumerate(command.args):
        possible_match = re.search(RE_MATCH_EXPENSE_NR, arg)
        if possible_match:
            idx = i
            currency_text = possible_match.group()
            currency_number = float(currency_text.replace(",", "."))
            # at least one number was found
            # ignoring numbers part of optional expense comment
            # first element treated as expense value
            break
    return idx, currency_number

class GroupExpenses:
    def __init__(self, currency_sign: str = None, users: dict = None, expenses: list = None, borrowed_amounts: list = None, percentages: dict = None):
        if borrowed_amounts is None:
            borrowed_amounts = []
        self.borrowed_amounts: list[tuple] = borrowed_amounts
        if expenses is None:
            expenses = []
        self.expenses: list[tuple] = expenses
        if users is None:
            users = []
        self.users: List[Dict[str, Optional[float]]] = users
        if currency_sign is None:
            currency_sign = plugin.read_config("currency_sign")
        self.currency_sign: str = currency_sign

    def __str__(self):
        group_str: str = "**Cashup group** \n\n"
        for i, user_info in enumerate(self.users):
            group_str += user_info['name']  # Access the 'name' from the dictionary
            if i < len(self.users) - 1:
                group_str += "; "

        # Display percentages only if not all users have a percentage of 1.0
        if self.users and any(user_info['percentage'] != 1.0 for user_info in self.users):
            group_str += "\n\nPercentages of users: \n"
            for user_info in self.users:
                user = user_info['name']
                percentage = user_info['percentage']
                group_str += f"* {user}: {percentage * 100}% \n"

        def c_or_n(comment: str | None) -> str:
            return comment if comment is not None else ""

        if len(self.expenses) > 0:
            group_str += "\n\nExpenses for the group per person: \n"
            for (from_name, amount, comment) in self.expenses:
                group_str += f"* {from_name} spend {print_currency(amount, self.currency_sign)} {c_or_n(comment)} \n"
        else:
            group_str += "\n\nNo expenses yet... \n"
        if len(self.borrowed_amounts) > 0:
            group_str += "\n\nPerson to person borrowments: \n"
            for (from_name, to_name, amount, comment) in self.borrowed_amounts:
                group_str += f"* {from_name} borrowed {to_name} {print_currency(amount, self.currency_sign)} {c_or_n(comment)} \n"
        else:
            group_str += "\n\nNothing borrowed yet... \n"

        distributed_list = self.distribute_expenses()
        distributed_text = ""
        if len(distributed_list) > 0:
            distributed_text = "\n\n"
            distributed_text += "Minimum of transactions to settle all debts: \n\n"
            for (from_name, to_name, amount) in distributed_list:
                distributed_text += f"* {from_name} owes {to_name} {print_currency(amount, self.currency_sign)} \n"

        return group_str + distributed_text


    def distribute_expenses(self):
        balance_group_expenses = self.__who_owes_who()
        balance_borrows = self.__sum_of_borrows()
        all_p_to_p_payments = balance_borrows + balance_group_expenses
        simplified_list = self.__simplify_tuple_list(all_p_to_p_payments)
        filtered_list = self.__filter_empty(simplified_list)
        positive_list = self.__rotate_for_positive_amounts_only(filtered_list)
        reduced_list = self.__reduce_expenses(positive_list)
        return reduced_list

    def __calculate_parts_to_pay(self):
        # Calculate total group expenses and mean
        group_expenses_sum, group_expenses_mean = self.__calculate_sum_and_mean_group_expenses()
        current_sum_per_group_member = self.__sum_of_expenses()

        # Determine if the group shares expenses evenly (all percentages == 1.0)
        all_equal_percentage = all(user['percentage'] == 1.0 for user in self.users)
        num_users = len(self.users)

        parts_to_pay = []
        for name, expenses in current_sum_per_group_member.items():
            user_info = self.get_user(name)

            if user_info is None:
                raise ValueError(f"User '{name}' not found in the registered users list.")

            # Calculate the expected share
            if all_equal_percentage:
                # Evenly split expenses
                expected_share = group_expenses_sum / num_users
            else:
                # Use the user's specific percentage
                expected_share = group_expenses_sum * user_info['percentage']

            # Calculate the difference between what the user paid and their expected share
            part_to_pay = expenses - expected_share

            parts_to_pay.append((name, part_to_pay))

        return parts_to_pay

    @staticmethod
    async def delete_group(search_room_id: str) -> bool:
        # delete group if exists
        return await clear_room_db_from_room_id(search_room_id)

    async def load_group(self, search_room_id: str):
        source: dict = await get_room_db_from_room_id(search_room_id)
        self.from_dict(source)

    async def save_group(self, room_id: str) -> bool:
        return await save_room_db_from_room_id(room_id, self.as_dict())

    def from_dict(self, source: dict):
        self.borrowed_amounts = source.get("borrowed_amounts", [])
        self.expenses = source.get("expenses", [])

        # Handle users
        flat_users = source.get("users", [])

        # Check if the users are in flat format (strings) or as dictionaries
        if all(isinstance(user, str) for user in flat_users):
            # Convert flat list of user names to list of user_info dictionaries
            self.users = [
                {
                    'name': user,
                    'percentage': 1.0  # Default to 1.0 for even split
                }
                for user in flat_users
            ]
        elif all(isinstance(user, dict) and 'name' in user for user in flat_users):
            # Already in the new format, just assign
            self.users = flat_users
        else:
            raise ValueError("Invalid format for users in the data source.")

        self.currency_sign = source.get("currency_sign", plugin.read_config("currency_sign"))

    def as_dict(self) -> dict:
        return {
            "borrowed_amounts": self.borrowed_amounts,
            "expenses": self.expenses,
            "users": self.users,
            "currency_sign": self.currency_sign
        }

    def is_empty(self) -> bool:
        return not self.users

    def has_something_to_share(self) -> bool:
        return len(self.expenses) > 0 or len(self.borrowed_amounts) > 0

    def set_currency_sign(self, new_sign: str):
        self.currency_sign = new_sign

    def register_user(self, name: str, percentage: Optional[float] = None) -> None:
        """Register a user with an optional expense percentage."""
        user_info = {
            'name': name,
            'percentage': percentage if percentage is not None else 1.0  # Default to 1.0 for even split
        }
        self.users.append(user_info)

    def get_user(self, name: str) -> Optional[Dict[str, float]]:
        """Retrieve user information by name."""
        for user in self.users:
            if user['name'] == name:
                return user
        return None

    def add_expense(self, name: str, amount: float, comment: str | None = None):
        if any(user['name'] == name for user in self.users):
            self.expenses.append((name, amount, comment))
        else:
            raise ValueError('User not found')

    def rm_last_expense_from(self, search_name: str) -> tuple | None:
        removed_expense: tuple | None = None
        # iterate backwards! From latest to oldest entry...
        for idx_reverse, (from_name, expense_value, comment) in enumerate(self.expenses[::-1]):
            if from_name == search_name:
                idx = len(self.expenses) - idx_reverse - 1
                removed_expense = self.expenses.pop(idx)
                break
        return removed_expense

    def reset_all(self):
        """Sets all expenses and borrowed amounts of every group member.

        Attention all previously captured expenses are lost!!!"""
        self.expenses = []
        self.borrowed_amounts = []

    def add_borrowed_amount(self, from_name: str, to_name: str, amount: float, comment: str | None = None):
        from_user = self.get_user(from_name)
        to_user = self.get_user(to_name)
        if from_user is not None and to_user is not None:
            borrowed = (from_name, to_name, amount, comment)
            self.borrowed_amounts.append(borrowed)
        else:
            none_user = from_user if from_user is None else to_user
            raise ValueError(f'User {none_user} not found')

    def rm_last_borrowed_amount(self, search_from_name: str, search_to_name: str) -> tuple | None:
        removed_loan: tuple | None = None
        # iterate backwards! From latest to oldest entry...
        for idx_reverse, (from_name, to_name, loan_value, comment) in enumerate(self.borrowed_amounts[::-1]):
            if from_name == search_from_name and to_name == search_to_name:
                idx = len(self.expenses) - idx_reverse - 1
                removed_loan = self.borrowed_amounts.pop(idx)
                break
        return removed_loan

    def __sum_of_expenses(self) -> Dict[str, float]:
        sum_of_expenses_per_user = {user['name']: 0 for user in self.users}

        for name, amount, _ in self.expenses:
            if name in sum_of_expenses_per_user:
                sum_of_expenses_per_user[name] += amount
            # Optional: Skip or log any expense entry for unregistered users.

        return sum_of_expenses_per_user

    def __sum_of_borrows(self):
        sum_of_borrows = {}
        for from_name, to_name, amount, _ in self.borrowed_amounts:  # ignoring comment
            print(from_name, to_name, amount)
            from_to = (to_name, from_name)
            if from_to in sum_of_borrows:
                sum_of_borrows[from_to] += amount
                print("add")
            else:
                sum_of_borrows[from_to] = amount
        flat_tuples = [(x[0][0], x[0][1], x[1]) for x in list(sum_of_borrows.items())]
        return flat_tuples

    def __calculate_sum_and_mean_group_expenses(self) -> (float, float):
        """Calculate and return the sum and mean of all expenses in the group."""
        current_sum_per_group_member = self.__sum_of_expenses()

        if current_sum_per_group_member:
            group_sum = sum(current_sum_per_group_member.values())
            group_mean = group_sum / len(self.users)
            return group_sum, group_mean
        else:
            return 0, 0

    def __who_owes_who(self) -> list[tuple[str, str, float]]:
        """Build strings of who owes who how much.
        Source is the JavaScript version found at:
        https://stackoverflow.com/questions/974922/algorithm-to-share-settle-expenses-among-a-group

        returns:
            output_texts: (array of str)
                Text elements per payment to
                settle expense among the group."""

        who_owes_who = []
        ordered_parts_to_pay = sorted(self.__calculate_parts_to_pay(), key=lambda d: d[1])
        sorted_people: list[str] = [part[0] for part in ordered_parts_to_pay]
        sorted_values_paid = [part[1] for part in ordered_parts_to_pay]
        i = 0
        j = len(sorted_people) - 1
        output_texts = []
        while i < j:
            debt = min(-(sorted_values_paid[i]), sorted_values_paid[j])
            sorted_values_paid[i] += debt
            sorted_values_paid[j] -= debt
            # generate output string
            if debt != 0.0:
                who_owes_who.append((sorted_people[i], sorted_people[j], debt))
                new_text = str(sorted_people[i]) + " owes " + str(sorted_people[j]) + " " + print_currency(debt, self.currency_sign)
                output_texts.append(new_text)
            if sorted_values_paid[i] == 0:
                i += 1
            if sorted_values_paid[j] == 0:
                j -= 1
        print(output_texts)
        return who_owes_who

    @staticmethod
    def __reduce_expenses(expenses: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
        # Create a dictionary to keep track of the net balance for each person
        balances = {}
        for payment in expenses:
            debtor, creditor, amount = payment

            # Update balances
            balances[debtor] = balances.get(debtor, 0) - amount
            balances[creditor] = balances.get(creditor, 0) + amount

        # Identify people who owe money and people who are owed money
        debtors = {person: balance for person, balance in balances.items() if balance < 0}
        creditors = {person: balance for person, balance in balances.items() if balance > 0}

        # Create a list of transactions to balance the expenses
        transactions = []
        for debtor, debtor_balance in debtors.items():
            while debtor_balance < 0:
                # Find the creditor with the highest balance
                creditor = max(creditors, key=creditors.get)

                # Calculate the amount to transfer from the creditor to the debtor
                transfer_amount = min(-debtor_balance, creditors[creditor])

                # Update balances and transactions
                debtor_balance += transfer_amount
                creditors[creditor] -= transfer_amount
                transactions.append((debtor, creditor, transfer_amount))

                # Remove the creditor from the list if their balance reaches zero
                if creditors[creditor] == 0:
                    del creditors[creditor]

        return transactions

    @staticmethod
    def __simplify_tuple_list(tuple_list):
        simplified_list = []
        for name1, name2, number in tuple_list:
            found = False
            for i, (n1, n2, total) in enumerate(simplified_list):
                if (name1 == n1 and name2 == n2) or (name1 == n2 and name2 == n1):
                    simplified_list[i] = (n1, n2, total + number if name1 == n1 else total - number)
                    found = True
                    break
            if not found:
                simplified_list.append((name1, name2, number))
        return simplified_list

    @staticmethod
    def __rotate_for_positive_amounts_only(lst):
        rotated_lst = []
        for tpl in lst:
            if tpl[2] < 0:
                rotated_tpl = (tpl[1], tpl[0], abs(tpl[2]))
            else:
                rotated_tpl = tpl
            rotated_lst.append(rotated_tpl)
        return rotated_lst

    @staticmethod
    def __filter_empty(tuple_list):
        filtered = []
        for tpl in tuple_list:
            if tpl[2] != 0:
                filtered.append(tpl)
        return filtered


async def register(command):
    """Register a set of people as a new group to share expenses"""
    response_input_error = (
        f"You need to register at least two users:  \n"
        "`cashup-register <user-name1> [<user1-percentage>]; <user-name2> [<user2-percentage>]; ...`  \n"
        "examples:  \n"
        "`cashup-register Alice 0.5; Bob 0.5` Alice and Bob will share expenses for the group according to the given percentages"
    )

    # Check if a group is already registered for this room
    previously_persisted_group = GroupExpenses()
    await previously_persisted_group.load_group(command.room.room_id)
    if not previously_persisted_group.is_empty():
        await plugin.respond_notice(
            command,
            """There is already a group registered for this room.
            I will do a quick cashup so no data will be lost when registering the new group.""",
        )
        await cash_up(command)

    if command.args:
        logger.debug(f"cashup-register called with {command.args}")
        # cashup-register called with ['Marius', '0,7;', 'Andrea', '0.3;']
        # cashup-register called with ['Marius;', 'Andrea;']
        # generate lists of names and optional percentages
        new_names = []
        new_percentages = []
        for arg in command.args:
            # remove all ; from arg element;
            arg = arg.replace(";", "")
            # find any numbers in string (eg: 12; 12,1; 12.1)
            match_arg_nr = re.search(RE_MATCH_EXPENSE_NR, arg)
            # returns a match object
            if match_arg_nr:
                # number (as string) found
                # replace "," of german numbers by a "." decimal point
                # convert the number to a real float number
                arg_float = float(match_arg_nr.group().replace(",", "."))
                if len(new_percentages) == (len(new_names) - 1):
                    new_percentages.append(arg_float)
                else:
                    await plugin.respond_notice(command, response_input_error)
                    return
            else:
                # (just in case) remove all "," from arg name element
                # don't do this for number elements as it harms percentage value
                arg = arg.replace(",", "")
                # skip empty fields
                # ("Name 0.1 ," -> "["Name", "0.1", ","] -> arg[2] "," -> replace "")
                if len(arg) == 0:
                    continue
                new_names.append(arg)
        if len(new_names) > 1:
            if len(new_percentages) == len(new_names):
                if sum(new_percentages) != 1:
                    await plugin.respond_notice(command, "The sum of all percentage values must be exactly 1!")
                    await plugin.respond_notice(command, response_input_error)
                    return
                new_group_not_even = GroupExpenses()
                for idx, name in enumerate(new_names):
                    new_group_not_even.register_user(name, new_percentages[idx])
                await new_group_not_even.save_group(command.room.room_id)
            else:
                new_group_even = GroupExpenses()
                for name in new_names:
                    new_group_even.register_user(name)  # Split evenly if no percentages
                await new_group_even.save_group(command.room.room_id)
        else:
            await plugin.respond_notice(command, response_input_error)
            return
    else:
        await plugin.respond_notice(command, response_input_error)
        return

    response_success = "Successfully registered a new group!"
    await plugin.respond_message(command, response_success)
    await print_room_state(command, send_dry_run_notice=False)



async def print_room_state(command, send_dry_run_notice: bool = True):
    """Read the database for the group registered for the current room [debugging helper function]"""
    loaded_group = GroupExpenses()
    await loaded_group.load_group(command.room.room_id)
    if loaded_group is not None:
        if send_dry_run_notice:
            print_notice = "**This is just a dry run and will not reset the groups state**"
            await plugin.respond_notice(command, print_notice)
        await plugin.respond_message(command, str(loaded_group))
    else:
        await plugin.respond_message(command, "No data to read!")


async def add_expense_for_user(command):
    """Adds a new expense for the given username."""
    response_input_error = (
        "You need to provide a previously registered user-name and expense value:  \n"
        "`cashup-add-expense <user-name> <expense-value>[€/$/etc.] [comment]` [optional]"
    )

    # Extract expense index and value
    expense_idx, expense_float = find_currency(command)
    user_name = ""

    # Determine the username based on command structure
    if expense_idx == 0:
        # No username provided, use sender's display name
        mxid: str = command.event.sender
        user_name = command.room.user_name(mxid)
    elif expense_idx == 1:
        # Username is the first argument
        user_name = command.args[0]

    # Optional comment extraction
    optional_comment = " ".join(command.args[expense_idx + 1:]) if len(command.args) > expense_idx + 1 else None

    # Check if both user_name and expense_float are valid
    if user_name and expense_float:
        try:
            # Load group data
            loaded_group = GroupExpenses()
            await loaded_group.load_group(command.room.room_id)

            # Attempt to add expense
            loaded_group.add_expense(user_name, expense_float, optional_comment)

        except AttributeError:
            await plugin.respond_notice(command, "Error: Could not load group data.")
            return
        except IndexError:
            await plugin.respond_notice(command, "Error: User not found in group.")
            return
        except ValueError:
            await plugin.respond_notice(command, "Error: Invalid expense value.")
            return

        # Save group and confirm success
        await loaded_group.save_group(command.room.room_id)
        await plugin.respond_message(
            command,
            f"Successfully added {print_currency(expense_float, loaded_group.currency_sign)} expense for {user_name}!"
        )
    else:
        # Respond with input error if username or expense is missing
        await plugin.respond_notice(command, response_input_error)


async def rm_expense_for_user(command: Command):
    response_input_error = (
        "You need to provide a previously registered user-name:  \n"
        "`cashup-rm-expense <user-name>`"
    )
    if len(command.args) != 1:
        await plugin.respond_notice(command, response_input_error)
    else:
        loaded_group = GroupExpenses()
        await loaded_group.load_group(command.room.room_id)
        if loaded_group.has_something_to_share():
            user_name = command.args[0]
            removed_expense = loaded_group.rm_last_expense_from(user_name)
            if removed_expense:
                currency = print_currency(removed_expense[1], loaded_group.currency_sign)
                await plugin.respond_notice(command, f"Successfully removed {currency} group expenses from {user_name}")
                await loaded_group.save_group(command.room.room_id)
                return
        await plugin.respond_notice(command, "Nothing to delete...")


async def add_loan(command: Command):
    """Adds a new loan from the given username to the given username"""
    response_input_error = (
        "You need to provide the names of previously registered user-names and an expense value:  \n"
        "`cashup-add-loan <from-name> <to-name> <loan>[€/$/etc.] [comment]` [optional]"
    )
    from_name: str = ""
    to_name: str = ""
    loan_idx, loan_float = find_currency(command)

    if len(command.args) >= 2 and loan_idx == 2:
        # command are: <from_name> <to_name> <expense-value>[€/$/etc.]
        from_name: str = command.args[0]
        to_name: str = command.args[1]
    if len(command.args) > loan_idx:
        # there is text behind the expense value
        optional_comment = " ".join(command.args[loan_idx+1:])
    else:
        optional_comment = None
    if from_name and to_name and loan_float:
        try:
            loaded_group = GroupExpenses()
            # init group from DB data
            await loaded_group.load_group(command.room.room_id)
            # Group.increase_expense throws IndexError when user_name not found
            loaded_group.add_borrowed_amount(from_name, to_name, loan_float, optional_comment)
        except (AttributeError, IndexError, ValueError) as _:
            await plugin.respond_notice(command, response_input_error)
            return
        await loaded_group.save_group(command.room.room_id)
        currency = print_currency(loan_float, loaded_group.currency_sign)
        await plugin.respond_message(
            command,
            f"Successfully added that {from_name} borrowed {to_name} {currency}",
        )
    else:
        await plugin.respond_notice(command, response_input_error)


async def rm_loan(command: Command):
    response_input_error = (
        "You need to provide two previously registered user-names:  \n"
        "`cashup-rm-loan <from-user-name> <to-user-name>`"
    )
    if len(command.args) != 2:
        await plugin.respond_notice(command, response_input_error)
    else:
        loaded_group = GroupExpenses()
        await loaded_group.load_group(command.room.room_id)
        if loaded_group.has_something_to_share():
            from_name = command.args[0]
            to_name = command.args[1]
            removed_loan = loaded_group.rm_last_borrowed_amount(from_name, to_name)
            if removed_loan:
                currency = print_currency(removed_loan[2], loaded_group.currency_sign)
                message = f"Successfully removed {currency} loan given from {from_name} to {to_name}"
                await plugin.respond_notice(command, message)
                await loaded_group.save_group(command.room.room_id)
                return
        await plugin.respond_notice(command, "Nothing to delete...")


async def cash_up(command):
    """Settle all registered expenses among the previously registered group."""

    loaded_group = GroupExpenses()
    await loaded_group.load_group(command.room.room_id)
    # make sure to respond in any way (None / AttributeError exception)
    if loaded_group.is_empty():
        response_error = "No cashup possible because there was no group registered for this room."
        await plugin.respond_notice(command, response_error)
    elif not loaded_group.has_something_to_share():
        await plugin.respond_notice(command, "No balancing of expenses needed.")
    else:
        await plugin.respond_message(command, str(loaded_group))
        loaded_group.reset_all()
        await loaded_group.save_group(command.room.room_id)


async def set_currency_sign(command):
    """Overwrite the group currency_value from the default one selected in cashup.yaml"""
    loaded_group = GroupExpenses()
    await loaded_group.load_group(command.room.room_id)
    if loaded_group is not None:
        if len(command.args) == 1:
            new_currency_sign = command.args[0]
            loaded_group.set_currency_sign(new_currency_sign)
            await loaded_group.save_group(command.room.room_id)
            response = f"Successfully updated the groups currency sign to: '{new_currency_sign}'"
            await plugin.respond_message(command, response)
        else:
            response = "Bad argument, please try again. Example: 'cashup-currency-sign $'"
            await plugin.respond_message(command, response)
    else:
        await plugin.respond_message(command, "No group registered, can not update the currency sign!")


setup()
