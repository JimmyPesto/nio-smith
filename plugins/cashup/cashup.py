# importing nio-stuff
from core.plugin import Plugin
import logging

# importing cash up stuff
import functools  # for reduce()

# importing regular expressions for parsing numbers
import re
from typing import List

logger = logging.getLogger(__name__)
plugin = Plugin("cashup", "General", "A very simple cashup plugin to share expenses in a group")

# find any numbers in string (eg: 12; 12,1; 12.1)
RE_MATCH_EXPENSE_NR = r'\d*[.,]?\d+'


def setup():
    # first command will be called when plugin name is called
    plugin.add_command(
        "cashup-register",
        register,
        "Resets existing room DB and initializes all group members for sharing expenses.",
        power_level=100,
    )
    plugin.add_command(
        "cashup-add-expense",
        add_expense_for_user,
        "Adds a new expense for the given user-name.",
    )
    plugin.add_command("cashup-print", print_room_state, "debug print function")
    plugin.add_command(
        "cashup",
        cash_up,
        "Settle all recorded expenses among the previously registered group.",
        power_level=50,
    )
    plugin.add_command("cashup-ae", add_expense_for_user, "Short form for `cashup-add-expense`")
    plugin.add_command("cashup-p", print_room_state, "Short form for `cashup-print`")

    plugin.add_command("chasup-set-currency-sign", set_currency_sign,
                       "Set a currency sign for a previously registered group in this room. "
                       "By default currency_sign from cashup.yaml will be used")

    """Defining a configuration values to be expected in the plugin's configuration file and reading the value
    Defines a currency_sign used for a nice output message
    """
    plugin.add_config("currency_sign", "€", is_required=True)


def print_currency(value: float, currency_sign: str = plugin.read_config("currency_sign")):
    clean_currency: str = "{:.2f}".format(value)
    clean_currency += currency_sign
    return clean_currency


class GroupPayments:
    def __init__(self, splits_evenly: bool = False, currency_sign: str = None):
        """Setup Group_payments instance
        Represents a group of people that want to share expenses.

        payments is an array of dict in the format
        that Cash_up class consumes
        each dict contains:
            * uid - user name
            * expenses - the sum of all expenses spend
            * [percentage] - optionally the percentage of the over all cost this person is going to pay

        Args:
            splits_evenly (bool)
                defines if the group splits all expenses evenly or every member pays a certain
                percentage of the over all cost
        """
        self.payments: List[dict] = []
        self.splits_evenly: bool = splits_evenly
        if currency_sign is None:
            currency_sign = plugin.read_config("currency_sign")
        self.currency_sign: str = currency_sign

    @classmethod
    def from_group_with_no_currency_sign(cls, old_group):
        new_group_with_currency_sign = cls(old_group.splits_evenly)  # selects default currency sign
        new_group_with_currency_sign.payments = old_group.payments
        return new_group_with_currency_sign

    def append_new_member(self, new_uid: str, new_percentage: float = None):
        """Adds a new member to this group

        throws ValueError when percentage value is demanded but not given.

        Args:
            new_uid (str): the new username to be added
            new_percentage (float): optional the percentage this person is going to pay"""
        new_member = {}
        if not self.splits_evenly:
            # group is defined as not splitting evenly
            if new_percentage is not None:
                # and a percentage value is given
                new_member = {
                    "uid": new_uid,
                    "percentage": new_percentage,
                    "expenses": 0,
                }
            else:
                # percentage value is demanded but not given
                error_msg = "cashup Group_payments append_new_member failed: " \
                            "members percentage is not defined for a group that does not split evenly"
                logger.error(error_msg)
                raise ValueError(error_msg, new_member)
        else:
            # group splits expenses evenly
            new_member = {"uid": new_uid, "expenses": 0}
        # store new member in groups list
        self.payments.append(new_member)

    def reset_all_expenses(self):
        """Sets all expenses to 0 for every group member.

        Attention all previously captured expenses are lost!!!"""
        for payment in self.payments:
            payment["expenses"] = 0

    def increase_expense(self, search_uid, new_expense: float):
        """Increases the current expenses of user with name search_uid
        by the given new_expense

        Args:
            search_uid (str): username whose expenses will be increased
            new_expense (float): the new expense that will be added
        """
        # find all payments where uid matches
        payment_to_increase = list(filter(lambda payment: payment["uid"] == search_uid, self.payments))
        # update first and hopefully only match
        # throws IndexError when search_uid not found
        payment_to_increase[0]["expenses"] += new_expense

    def set_currency_sign(self, new_sign: str):
        self.currency_sign = new_sign

    def __str__(self):
        """Simple function to get a human-readable string of this groups state"""
        group_str: str = f"**Group**: splits_evenly: {self.splits_evenly},  \n"
        for payment in self.payments:
            name = payment["uid"]
            expense = payment["expenses"]
            group_str += f"{name} spend {print_currency(expense, self.currency_sign)}"
            if not self.splits_evenly:
                percentage = payment["percentage"] * 100
                group_str += f" and will pay {percentage}% of the over all cost  \n"
            else:
                group_str += f"  \n"
        return group_str


class PersistentGroups:
    """Setup Persistent_groups instance
    Simple wrapper for persisting groups in some kind of database

    Args:
        store
            The object used to interact with the database
    """

    def __init__(self, store: Plugin):
        self.store = store

    async def delete_group(self, search_room_id: str) -> bool:
        # delete group if exists
        return await self.store.clear_data(search_room_id)

    async def load_group(self, search_room_id: str) -> GroupPayments:
        loaded_group: GroupPayments = await self.store.read_data(search_room_id)
        # Workaround for backwards compatibility to old builds (old GroupPayments did not include currency_sign)
        if loaded_group is not None:
            try:
                _ = loaded_group.currency_sign
            except AttributeError:
                loaded_group = GroupPayments.from_group_with_no_currency_sign(loaded_group)
                loaded_group.currency_sign = plugin.read_config("currency_sign")
        return loaded_group

    async def save_group(self, room_id: str, group_to_save: GroupPayments) -> bool:
        return await self.store.store_data(room_id, group_to_save)


pg = PersistentGroups(plugin)


class Cashup:
    def __init__(self, group: GroupPayments):
        """Setup Cash_up algorithm
        For a set of people who owe each other some money or none
        this algorithm can settle expense among this group.

        Optionally it can be specified how much percentage of
        the over all expenses should be paid by each person.
        If not specified the expenses are distributed equally.
        Args:
            group (Group_payments): Object representing a groups
            expenses and how they want to split these
        """
        self.group = group

    def distribute_expenses(self):
        """distribute the given expenses within the group
        and return who owes who texts

        returns: (array of str)
            Text elements per payment to
            settle expense among the group."""
        self._calculate_sum_and_mean_group_expenses()
        self._calculate_parts_to_pay()
        return self._who_owes_who()

    def _calculate_sum_and_mean_group_expenses(self):
        """calculate the sum & mean of all expenses in the group"""
        self._sum_group_expenses = functools.reduce(lambda acc, curr: acc+int(curr["expenses"]), self.group.payments, 0)
        self._mean_group_expenses = self._sum_group_expenses / len(self.group.payments)

    def _calculate_parts_to_pay(self):
        """calculate the parts each person has to pay
        depending on _split_uneven or not"""
        if self.group.splits_evenly:
            self._parts_to_pay = [
                {
                    "uid": payment["uid"],
                    "has_to_pay": (payment["expenses"] - self._mean_group_expenses),
                }
                for payment in self.group.payments
            ]
        else:
            self._parts_to_pay = [
                {
                    "uid": payment["uid"],
                    "has_to_pay": (payment["expenses"] - (self._sum_group_expenses * payment["percentage"])),
                }
                for payment in self.group.payments
            ]

    def _who_owes_who(self):
        """Build strings of who owes who how much.
        Source is the JavaScript version found at:
        https://stackoverflow.com/questions/974922/algorithm-to-share-settle-expenses-among-a-group

        returns:
            output_texts: (array of str)
                Text elements per payment to
                settle expense among the group."""
        # some function
        ordered_parts_to_pay = sorted(self._parts_to_pay, key=lambda d: d["has_to_pay"])
        sorted_people = [part["uid"] for part in ordered_parts_to_pay]
        sorted_values_paid = [part["has_to_pay"] for part in ordered_parts_to_pay]
        i = 0
        j = len(sorted_people) - 1
        output_texts = []
        while i < j:
            debt = min(-(sorted_values_paid[i]), sorted_values_paid[j])
            sorted_values_paid[i] += debt
            sorted_values_paid[j] -= debt
            # generate output string
            if debt != 0.0:
                new_text = str(sorted_people[i]) + " owes " + str(sorted_people[j]) + " " \
                           + print_currency(debt, self.group.currency_sign)
                output_texts.append(new_text)
            if sorted_values_paid[i] == 0:
                i += 1
            if sorted_values_paid[j] == 0:
                j -= 1
        return output_texts


async def register(command):
    """Register a set of people as a new group to share expenses"""
    response_input_error = (
        f"You need to register at least two users:  \n"
        "`cashup-register <user-name1> [<user1-percentage>]; <user-name2> [<user2-percentage>]; ...` [optional]  \n"
        "examples:  \n"
        "`cashup-register A 0.2; B 0.8;` A pays 20%, B pays 80% or `cashup-register A; B;` to split expenses evenly"
    )
    # if there is a group registered for this room already
    # run a cashup so old data will be shown to the users
    # before deleting it
    previously_persisted_group: GroupPayments = await pg.load_group(command.room.room_id)
    if previously_persisted_group is not None:
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
        if len(new_names) > 1 and len(new_names) == len(new_percentages):
            # every name got a percentage value
            all_percentages_sum = sum(new_percentages)
            if all_percentages_sum != 1:
                await plugin.respond_notice(command, "The sum of all percentage values shall be exactly 1!"
                                                     "Registration of group failed...")
                await plugin.respond_notice(command, response_input_error)
                return
            new_group_not_even = GroupPayments(splits_evenly=False)
            for idx, name in enumerate(new_names):
                # create a new group member with split percentage
                new_group_not_even.append_new_member(name, new_percentages[idx])
            # persist new group for current room id
            await pg.save_group(command.room.room_id, new_group_not_even)
        elif len(new_percentages) == 0 and len(new_names) > 1:
            # no name got a percentage value
            new_group_even = GroupPayments(splits_evenly=True)
            for name in new_names:
                # create a new group member without split percentage (split expenses equally)
                new_group_even.append_new_member(name)
            # persist new group for current room id
            await pg.save_group(command.room.room_id, new_group_even)
        else:
            # sth went terribly wrong
            await plugin.respond_notice(command, response_input_error)
            return
    else:
        # no command args defined
        await plugin.respond_notice(command, response_input_error)
        return
    response_success = "Successfully registered a new group:"
    await plugin.respond_message(command, response_success)
    await print_room_state(command)


async def print_room_state(command):
    """Read the database for the group registered for the current room [debugging helper function]"""
    loaded_group: GroupPayments = await pg.load_group(command.room.room_id)
    if loaded_group is not None:
        response = loaded_group.__str__()
        await plugin.respond_message(command, response)
    else:
        await plugin.respond_message(command, "No data to read!")


async def add_expense_for_user(command):
    """Adds a new expense for the given username"""
    response_input_error = (
        "You need to provide a previously registered user-name and expense value:  \n"
        "`cashup-add-expense <user-name> <expense-value>[€/$/etc.] [comment]` [optional]"
    )
    user_name: str = ""
    expense_str: str = ""

    possible_expense_idxs = [i for i, item in enumerate(command.args) if re.search(RE_MATCH_EXPENSE_NR, item)]
    if len(possible_expense_idxs) > 0:
        # at least one number was found
        # ignoring numbers part of optional expense comment
        # first element treated as expense value
        expense_idx = possible_expense_idxs[0]
        expense_str = re.search(RE_MATCH_EXPENSE_NR, command.args[expense_idx]).group()
        if expense_idx == 0:
            # first command arg is <expense-value>[€/$/etc.]
            # user seems has not provided a <user-name>
            # maybe the user wants to increase for himself
            # use display_name of user as <user-name>
            mxid: str = command.event.sender
            user_name = command.room.user_name(mxid)
        elif expense_idx == 1:
            # first command arg is <user-name>
            user_name = command.args[0]

    if user_name and expense_str:
        expense_float = float(expense_str.replace(",", "."))
        try:
            # Persistent_groups.load_group throws AttributeError when group not found
            loaded_group: GroupPayments = await pg.load_group(command.room.room_id)
            # Group.increase_expense throws IndexError when user_name not found
            loaded_group.increase_expense(user_name, expense_float)
        except (AttributeError, IndexError) as _:
            await plugin.respond_notice(command, response_input_error)
            return
        await pg.save_group(command.room.room_id, loaded_group)
        await plugin.respond_message(
            command,
            f"Successfully added {print_currency(expense_float, loaded_group.currency_sign)} expense for {user_name}!",
        )
    else:
        await plugin.respond_notice(command, response_input_error)


async def cash_up(command):
    """Settle all registered expenses among the previously registered group."""
    try:
        loaded_group: GroupPayments = await pg.load_group(command.room.room_id)
        # make sure to respond in any way (None / AttributeError exception)
        if loaded_group is None:
            raise AttributeError
    except AttributeError:
        response_error = "No cashup possible because there was no group registered for this room."
        await plugin.respond_notice(command, response_error)
        return
    cashup = Cashup(loaded_group)
    message: str = ""
    who_owes_who_texts = cashup.distribute_expenses()
    # check if any payments should be done
    if len(who_owes_who_texts) > 0:
        message += f"**Result of group cashup**:  \n"
        for line in who_owes_who_texts:
            message += f"{line}  \n"
        await plugin.respond_message(command, message)
    else:
        await plugin.respond_notice(command, "No balancing of expenses needed.")
    loaded_group.reset_all_expenses()
    await pg.save_group(command.room.room_id, loaded_group)


async def set_currency_sign(command):
    """Overwrite the group currency_value from the default one selected in cashup.yaml"""
    loaded_group: GroupPayments = await pg.load_group(command.room.room_id)
    if loaded_group is not None:
        if len(command.args) == 1:
            new_currency_sign = command.args[0]
            loaded_group.set_currency_sign(new_currency_sign)
            await pg.save_group(command.room.room_id, loaded_group)
            response = f"Successfully updated the groups currency sign to: '{new_currency_sign}'"
            await plugin.respond_message(command, response)
        else:
            response = "Bad argument, please try again. Example: 'cashup-currency-sign $'"
            await plugin.respond_message(command, response)
    else:
        await plugin.respond_message(command, "No group registered, can not update the currency sign!")


setup()
