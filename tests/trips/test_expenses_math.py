from decimal import Decimal

from trips.expenses import (
    ExpenseInput,
    Participant,
    aggregate_wallets,
    compute_balances,
    settle,
    split_amount,
)

D = Decimal


class TestSplitAmount:
    def test_even_split(self):
        assert split_amount(D("9.00"), 3) == [D("3.00"), D("3.00"), D("3.00")]

    def test_largest_remainder(self):
        assert split_amount(D("10.00"), 3) == [D("3.34"), D("3.33"), D("3.33")]

    def test_single(self):
        assert split_amount(D("10.00"), 1) == [D("10.00")]

    def test_one_cent_among_three(self):
        assert split_amount(D("0.01"), 3) == [D("0.01"), D("0.00"), D("0.00")]

    def test_zero_participants(self):
        assert split_amount(D("10.00"), 0) == []

    def test_sum_is_exact(self):
        parts = split_amount(D("100.00"), 7)
        assert sum(parts) == D("100.00")


class TestChildAttribution:
    def test_issue_example_single_parent_units(self):
        # 4 adults + 2 children, €60 split six ways; each child charged to one adult.
        participants = [
            Participant(1, unit_id=10, unit_shared=True),
            Participant(2, unit_id=20, unit_shared=True),
            Participant(3),
            Participant(4),
            Participant(5, is_child=True, unit_id=10, unit_shared=True),
            Participant(6, is_child=True, unit_id=20, unit_shared=True),
        ]
        expenses = [ExpenseInput(D("60.00"), payer_id=3, sharer_ids=(1, 2, 3, 4, 5, 6))]
        balances, warnings = compute_balances(participants, expenses)
        assert warnings == set()
        assert 5 not in balances and 6 not in balances
        assert balances[1]["owed"] == D("20.00")
        assert balances[2]["owed"] == D("20.00")
        assert balances[3]["owed"] == D("10.00")
        assert balances[4]["owed"] == D("10.00")
        assert balances[3]["net"] == D("50.00")
        assert sum(b["net"] for b in balances.values()) == D("0.00")

    def test_couple_unit_two_children(self):
        participants = [
            Participant(1, unit_id=10, unit_shared=True),
            Participant(2, unit_id=10, unit_shared=True),
            Participant(3),
            Participant(4),
            Participant(5, is_child=True, unit_id=10, unit_shared=True),
            Participant(6, is_child=True, unit_id=10, unit_shared=True),
        ]
        expenses = [ExpenseInput(D("60.00"), payer_id=3, sharer_ids=(1, 2, 3, 4, 5, 6))]
        balances, _ = compute_balances(participants, expenses)
        assert balances[1]["owed"] == D("20.00")
        assert balances[2]["owed"] == D("20.00")

    def test_child_with_single_adult_pays_full(self):
        participants = [
            Participant(1, unit_id=10),
            Participant(2, is_child=True, unit_id=10),
        ]
        expenses = [ExpenseInput(D("20.00"), payer_id=1, sharer_ids=(1, 2))]
        balances, _ = compute_balances(participants, expenses)
        assert balances[1]["owed"] == D("20.00")
        assert 2 not in balances

    def test_child_share_odd_cent_split(self):
        # child share 5.01 split between two adults -> 2.51 / 2.50
        participants = [
            Participant(1, unit_id=10),
            Participant(2, unit_id=10),
            Participant(3, is_child=True, unit_id=10),
        ]
        expenses = [ExpenseInput(D("15.03"), payer_id=1, sharer_ids=(1, 2, 3))]
        balances, _ = compute_balances(participants, expenses)
        # each adult owns 5.01; child's 5.01 -> 2.51 + 2.50
        assert balances[1]["owed"] == D("7.52")
        assert balances[2]["owed"] == D("7.51")

    def test_child_without_unit_keeps_share_and_warns(self):
        participants = [Participant(1), Participant(2, is_child=True)]
        expenses = [ExpenseInput(D("20.00"), payer_id=1, sharer_ids=(1, 2))]
        balances, warnings = compute_balances(participants, expenses)
        assert warnings == {2}
        assert balances[2]["owed"] == D("10.00")

    def test_unit_with_only_children_warns(self):
        participants = [
            Participant(1),
            Participant(2, is_child=True, unit_id=10),
        ]
        expenses = [ExpenseInput(D("20.00"), payer_id=1, sharer_ids=(1, 2))]
        balances, warnings = compute_balances(participants, expenses)
        assert warnings == {2}

    def test_child_payer_credit_moves_to_adults(self):
        participants = [
            Participant(1, unit_id=10),
            Participant(2, unit_id=10),
            Participant(3, is_child=True, unit_id=10),
        ]
        # the child "paid" (parent used family money) and everyone consumed
        expenses = [ExpenseInput(D("30.00"), payer_id=3, sharer_ids=(1, 2, 3))]
        balances, _ = compute_balances(participants, expenses)
        assert 3 not in balances
        # 30 paid split to adults 15/15; each owes own 10 + half child's 10 = 15
        assert balances[1]["net"] == D("0.00")
        assert balances[2]["net"] == D("0.00")


class TestWalletsAndSettlement:
    def test_participant_without_unit_is_solo(self):
        participants = [Participant(1), Participant(2)]
        balances = {1: {"net": D("10.00")}, 2: {"net": D("-10.00")}}
        wallet_nets, _ = aggregate_wallets(participants, balances)
        assert set(wallet_nets) == {("solo", 1), ("solo", 2)}

    def test_shared_unit_aggregates_members(self):
        participants = [
            Participant(1, unit_id=10, unit_shared=True),
            Participant(2, unit_id=10, unit_shared=True),
        ]
        balances = {1: {"net": D("15.00")}, 2: {"net": D("-5.00")}}
        wallet_nets, _ = aggregate_wallets(participants, balances)
        # intra-unit debts cancel: net wallet = 10
        assert wallet_nets == {("unit", 10): D("10.00")}

    def test_non_shared_unit_keeps_members_solo(self):
        participants = [
            Participant(1, unit_id=10, unit_shared=False),
            Participant(2, unit_id=10, unit_shared=False),
        ]
        balances = {1: {"net": D("15.00")}, 2: {"net": D("-5.00")}}
        wallet_nets, _ = aggregate_wallets(participants, balances)
        assert wallet_nets == {("solo", 1): D("15.00"), ("solo", 2): D("-5.00")}

    def test_settle_minimizes_transactions(self):
        wallet_nets = {
            ("solo", 1): D("50.00"),
            ("solo", 2): D("-20.00"),
            ("solo", 3): D("-10.00"),
            ("solo", 4): D("-20.00"),
        }
        settlements = settle(wallet_nets)
        assert len(settlements) <= 3
        # every debtor is fully settled and the creditor fully paid
        assert sum(s["amount"] for s in settlements) == D("50.00")
        for s in settlements:
            assert s["to"] == ("solo", 1)

    def test_settle_is_deterministic(self):
        wallet_nets = {
            ("solo", 1): D("30.00"),
            ("solo", 2): D("-30.00"),
        }
        assert settle(wallet_nets) == [
            {"from": ("solo", 2), "to": ("solo", 1), "amount": D("30.00")}
        ]

    def test_settle_empty(self):
        assert settle({("solo", 1): D("0.00")}) == []

    def test_settle_debtor_split_across_creditors(self):
        wallet_nets = {
            ("solo", 1): D("-50.00"),
            ("solo", 2): D("30.00"),
            ("solo", 3): D("20.00"),
        }
        settlements = settle(wallet_nets)
        assert len(settlements) == 2
        assert all(s["from"] == ("solo", 1) for s in settlements)
        assert sum(s["amount"] for s in settlements) == D("50.00")


class TestSingleFamilyTrip:
    def _participants(self, shared):
        return [
            Participant(1, unit_id=10, unit_shared=shared),
            Participant(2, unit_id=10, unit_shared=shared),
            Participant(3, is_child=True, unit_id=10, unit_shared=shared),
        ]

    def test_shared_wallet_settles_to_zero(self):
        participants = self._participants(shared=True)
        expenses = [ExpenseInput(D("30.00"), payer_id=1, sharer_ids=(1, 2, 3))]
        balances, _ = compute_balances(participants, expenses)
        wallet_nets, _ = aggregate_wallets(participants, balances)
        assert settle(wallet_nets) == []

    def test_separate_wallet_settles_between_parents(self):
        participants = self._participants(shared=False)
        expenses = [ExpenseInput(D("30.00"), payer_id=1, sharer_ids=(1, 2, 3))]
        balances, _ = compute_balances(participants, expenses)
        # parent 1 paid 30, each owes 15 (own 10 + half child's 10)
        assert balances[1]["net"] == D("15.00")
        assert balances[2]["net"] == D("-15.00")
        wallet_nets, _ = aggregate_wallets(participants, balances)
        settlements = settle(wallet_nets)
        assert settlements == [
            {"from": ("solo", 2), "to": ("solo", 1), "amount": D("15.00")}
        ]
