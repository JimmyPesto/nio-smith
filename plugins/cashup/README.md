Plugin: cashup
===
For a set of people who owe each other some money this plugin can settle expenses among this group.

Optionally it can be specified how much percentage of the over all expenses should be paid by each person.
If not specified the expenses are distributed equally.

This plugin is maintained by [JimmyPesto](https://github.com/JimmyPesto/nio-smith).

## Commands

### cashup
Usage: `cashup`   
Settle all recorded expenses among the previously registered group

### cashup-register
Usage: `cashup-register <user-name1> [<user1-percentage>]; <user-name2> [<user2-percentage>]; [...]` [optional]  
Initializes all group members for sharing expenses. You need to register at least two users separated by a ";" sign. If there is already a group registered for this room, a regular `cashup` will be done before overwriting the old entries in the database. It is recommended to register users based on their display name so useres can add expenses for them selfes without having to write their name.

Examples:  
* `cashup-register Alice; Bob;` `Alice` and `Bob` split expenses evenly
* `cashup-register A 0.2; B 0.8;` `A` pays 20%, `B` pays 80%

### cashup-add-expense or cashup-ae
Usage: `cashup-add-expense <user-name> <expense-value>[€/$]` or `cashup-ae <user-name> <expense-value>[€/$]` [optional]   
Adds a new expense for the given user-name. If a users display name was registered before, this user can add expenses for himself without specifying a `<user-name>`.

Examples:
* `cashup-add-expense Alice 10€` adds 10 expense for a user registered as `Alice` 
* `cashup-add-expense Alice 10` adds 10 expense for a user registered as `Alice` 
* `cashup-add-expense 10€` adds 10 expense for a user registered with his matrix display name  


### cashup-rm-expense
Usage: `cashup-rm-expense <user-name>`   
Remove the last expense added for the given user-name.

Examples:
* `cashup-rm-expense Alice` removes the expense previously added by the user registered as `Alice`


### cashup-add-loan or cashup-al
Usage: `cashup-add-loan <from-user-name> <to-user-name> <loan>[€/$]` or `cashup-al <user-name> <from-user-name> <expense-value>[€/$]` [optional]   
Adds a new expense for the given user-name. If a users display name was registered before, this user can add expenses for himself without specifying a `<user-name>`.

Examples:
* `cashup-add-loan Alice Bob 10€` adds a loan of 10 given from a user registered as `Alice` to a user registered as `Bob` 
* `cashup-al Alice Bob 10` adds a loan of 10 given from a user registered as `Alice` to a user registered as `Bob`


### cashup-rm-loan
Usage: `cashup-rm-loan <from-user-name> <to-user-name>`   
Remove the last loan added from a given user-name to another.

Examples:
* `cashup-rm-loan Alice Bob` removes the loan previously given from the user registered as `Alice` to `Bob`

### cashup-print or cashup-p
Usage: `cashup-print` or `cashup-p`  
Prints the current room state (for debuging).

### cashup-currency-sign
Usage: `!n cashup-currency-sign $`  
Changes the default `currency_sign` defined in the configuration file for a previously registered group.

## Configuration
Configuration options in `cashup.yaml`  
- `currency_sign`: A string containing the currency sign of your local currency (eg:"€","$"). Default value: "€"

## External Requirements
- none
