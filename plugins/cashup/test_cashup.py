from cashup import GroupExpenses

import pytest

DEFAULT_GROUP = ['Alice', 'Bob', 'Charlie']
UNEVEN_SHARE_GROUP = ['Alice', 'Bob']

DEFAULT_GROUP_A_EXPENSES = [('Alice', 100, "comment"), ('Bob', 50, None), ('Charlie', 30, None)]
DEFAULT_GROUP_B_EXPENSES = [('Alice', 23, None), ('Bob', 123, None), ('Charlie', 100, "c1 c2 c3")]

DEFAULT_GROUP_A_BORROWED = [('Alice', 'Bob', 23, None), ('Bob', 'Charlie', 100, "comment1 comment2 comment3")]
DEFAULT_GROUP_B_BORROWED = [('Alice', 'Bob', 23, None), ('Bob', 'Alice', 100, None), ('Bob', 'Charlie', 1, None),
                            ('Bob', 'Charlie', 10, None), ('Alice', 'Charlie', 10, None)]
DEFAULT_GROUP_D_BORROWED = [('Alice', 'Bob', 10, None), ('Charlie', 'Bob', 10, None), ('Charlie', 'Alice', 100, None)]


def add_expense_to_group(expense: list[tuple], group: GroupExpenses) -> GroupExpenses:
    for (member, expense, comment) in expense:
        group.add_expense(member, expense)
    return group


def add_borrowed_to_group(borrowed: list[tuple], group: GroupExpenses) -> GroupExpenses:
    for borrow in borrowed:
        group.add_borrowed_amount(*borrow)
    return group


def assert_balance_to_include(test_group: GroupExpenses, correct_results: list[tuple]):
    balance = test_group.distribute_expenses()
    for result in correct_results:
        assert result in balance, "Expected result not found in balance!"



def get_default_group() -> GroupExpenses:
    group = GroupExpenses()
    for member in DEFAULT_GROUP:
        group.register_user(member)
    return group


def get_uneven_group() -> GroupExpenses:
    group = GroupExpenses()
    group.register_user('Alice', percentage=0.1)
    group.register_user('Bob', percentage=0.9)
    return group


@pytest.fixture()
def default_group() -> GroupExpenses:
    return get_default_group()


@pytest.fixture()
def uneven_group() -> GroupExpenses:
    return get_uneven_group()


@pytest.mark.parametrize("group, expense, expected_balance_to_include",[
    (get_default_group(), [("Charlie", 300, None)], [('Alice', 'Charlie', 100.0), ('Bob', 'Charlie', 100.0)]),
    (get_default_group(), DEFAULT_GROUP_A_EXPENSES, [('Charlie', 'Alice', 30.0), ('Bob', 'Alice', 10.0)]),
    (get_default_group(), DEFAULT_GROUP_B_EXPENSES, [('Alice', 'Charlie', 18.0), ('Alice', 'Bob', 41.0)]),
    (get_uneven_group(), [('Bob', 100, None), ('Alice', 10, None)], [('Alice', 'Bob', 1.0)]),
])
def test_cashup_split_group_payments(group, expense, expected_balance_to_include):
    add_expense_to_group(expense, group)
    assert_balance_to_include(group, expected_balance_to_include)


@pytest.mark.parametrize("borrowed, expected_balance_to_include",[
    (DEFAULT_GROUP_A_BORROWED, [('Charlie', 'Bob', 77), ('Charlie', 'Alice', 23)]),
    (DEFAULT_GROUP_D_BORROWED, [('Bob', 'Charlie', 20), ('Alice', 'Charlie', 90)]),
])
def test_cashup_split_p2p_payments(default_group, borrowed, expected_balance_to_include):
    default_group = add_borrowed_to_group(borrowed, default_group)
    assert_balance_to_include(default_group, expected_balance_to_include)


@pytest.mark.parametrize("expense, borrowed, expected_balance_to_include", [
    (DEFAULT_GROUP_A_EXPENSES, DEFAULT_GROUP_A_BORROWED, [('Charlie', 'Bob', 67.0), ('Charlie', 'Alice', 63.0)])
])
def test_cashup_combo_group_payments_and_borrowments(default_group, expense, borrowed, expected_balance_to_include):
    default_group = add_expense_to_group(expense, default_group)
    default_group = add_borrowed_to_group(borrowed, default_group)
    assert_balance_to_include(default_group, expected_balance_to_include)


def test_remove_expense(default_group):
    default_group = add_expense_to_group(DEFAULT_GROUP_A_EXPENSES+DEFAULT_GROUP_A_EXPENSES, default_group)
    removed_expense = default_group.rm_last_expense_from("Bob")
    assert len(default_group.expenses) == len(DEFAULT_GROUP_A_EXPENSES)*2-1
    assert isinstance(removed_expense, tuple)
    assert removed_expense[0] == "Bob"
    assert removed_expense[1] == 50
    # there is some other Bob expense left
    left_over_bob_expenses = list(filter(lambda expense: expense[0] == "Bob", default_group.expenses))
    assert len(left_over_bob_expenses) > 0


def test_remove_loan(default_group):
    default_group = add_borrowed_to_group(DEFAULT_GROUP_B_BORROWED+DEFAULT_GROUP_B_BORROWED, default_group)
    removed_loan = default_group.rm_last_borrowed_amount('Bob', 'Charlie')
    assert len(default_group.borrowed_amounts) == len(DEFAULT_GROUP_B_BORROWED)*2-1
    assert isinstance(removed_loan, tuple)
    assert removed_loan[0] == "Bob"
    assert removed_loan[1] == "Charlie"
    assert removed_loan[2] == 10
    # there is some other 'Bob', 'Charlie' left
    left_over_bob_charlie_loans = list(filter(
        lambda loan: loan[0] == "Bob" and loan[1] == "Charlie", default_group.borrowed_amounts))
    assert len(left_over_bob_charlie_loans) > 0
