import smartpy as sp

Config = sp.io.import_script_from_url("file:./_config.py", name = "Config").Config

class Admin:
  def is_administrator(self, address):
    return address == self.data.admin
  def verify_sender_admin(self):
    sp.verify(self.is_administrator(sp.sender), message = "NOT_ADMIN")
  @sp.entry_point
  def set_administrator(self, address):
    sp.set_type(address, sp.TAddress)
    self.verify_sender_admin()
    self.data.admin = address

class HelpUkraine(sp.Contract, Admin):
  """
  TYPES DEFINITION
  """
  T_SPLIT = sp.TRecord(
    # the target of the split
    address = sp.TAddress,
    # the percentage per mile
    pct = sp.TNat,
  )
  T_SPLITS = sp.TList(T_SPLIT)

  """
  INITIALISATION
  """
  def __init__(self, admin):
    # define the storage type
    self.init_type(sp.TRecord(
      admin = sp.TAddress,
      splits = HelpUkraine.T_SPLITS,
    ))
    # init the storage
    self.init(sp.record(
      admin = admin,
      splits = sp.list([], t = HelpUkraine.T_SPLIT),
    ))

  """
  VERIFICATION
  """
  @sp.private_lambda(with_storage = None, with_operations = False, wrap_call = True)
  def verify_splits(self, splits):
    pcts_sum = sp.local("pcts_sum", 0)
    sp.for split in splits:
      pcts_sum.value += split.pct
    sp.verify(pcts_sum.value == 1000, message = "INVALID_SPLITS")

  """
  ENTRY POINTS
  """
  # the account can receive tez
  @sp.entry_point
  def default(self, unit):
    sp.set_type(unit, sp.TUnit)
    pass

  # withdraw the balance by splitting with the shares
  @sp.entry_point
  def withdraw(self, params):
    sp.set_type(params, sp.TUnit)
    to_send = sp.local("to_send", sp.balance)
    # loop through the shares to distribute the contract's balance
    sp.for split in self.data.splits:
      sp.send(split.address, sp.split_tokens(to_send.value, split.pct, 1000))

  # update the splits
  @sp.entry_point
  def set_splits(self, splits):
    sp.set_type(splits, HelpUkraine.T_SPLITS)
    self.verify_sender_admin()
    self.verify_splits(splits)
    self.data.splits = splits



if "templates" not in __name__:

  @sp.add_test(name = "HelpUkraine_units", is_default = True)
  def test():
    scenario = sp.test_scenario()
    scenario.h1("Help Ukraine contract tests")
    scenario.table_of_contents()

    # sp.test_account generates ED25519 key-pairs deterministically:
    admin = sp.test_account("Administrator")
    attacker = sp.test_account("attacker")
    donationA = sp.test_account("donationA")
    donationB = sp.test_account("donationB")
    random = sp.test_account("random")
    
    # Let's display the accounts:
    scenario.h2("Accounts")
    scenario.show([ admin, attacker, donationA, donationB, random ])
    C = HelpUkraine(
      admin = admin.address,
    )
    # some funds were donated to the contract
    C.set_initial_balance(sp.tez(100))
    scenario += C

    # withdraw when no split should do nothing
    C.withdraw().run(sender = random)
    scenario.verify(C.balance == sp.tez(100))

    # set splits
    C.set_splits(sp.list([
      sp.record(
        address = donationA.address,
        pct = 500,
      ),
      sp.record(
        address = donationB.address,
        pct = 500,
      )
    ])).run(
      sender = admin,
    )

    # set splits but wrong sum
    C.set_splits(sp.list([
      sp.record(
        address = donationA.address,
        pct = 500,
      ),
      sp.record(
        address = donationB.address,
        pct = 501,
      )
    ])).run(
      sender = admin,
      valid = False,
    )

    # only admin can update splits
    C.set_splits(sp.list([
      sp.record(
        address = donationA.address,
        pct = 500,
      ),
      sp.record(
        address = donationB.address,
        pct = 500,
      )
    ])).run(
      sender = attacker,
      valid = False,
    )

    # withdraw the balance
    C.withdraw().run(sender = random)
    scenario.verify(C.balance == sp.tez(0))
  

  sp.add_compilation_target(
    "HelpUkraine", 
    HelpUkraine(
      admin = sp.address(Config.address_admin),
    )
  )
