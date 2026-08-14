NOTE(g):

The reason provisioning gets it's own storage directory is that provisioning storage is a weird thing.

You need to know how many volumes to provision, which requires understanding the algorthm being applied to create them (say a RAID-5 vs a RAID-1, different numbers of volumes are needed).

Because this is totally unique to a given Storage Handler Stack, this cant be a normal function, or else we have to make a special rule for executing Functions.  I dont want special rules for Functions, I want them to be dead simple to use, so complex things can be performed safely, because they cant be executed incorrectly, as they take NO ARGUMENTS.  This is a safety precaution to reduce the chances of destroying your production system with a type.  At least it cant happen in calling things or state, or environment, it has to happen in code, which you've hopefully tested more thoroughly than environments can be tested.

To fix all this, I created the field: storage_handler_stack.script_provision

When we need to provision a Handler Stack, we just call this script and it does everything.  No messing about with Function stacks here, and the nightmare that would be.  Function Stacks are great for storage functions, because they handle the whole stack.  We want to provision FOR the stack.

Needless to say, each use of a Handler Stack in a Storage will need script_provision to be filled in, or no provisioning will occur (but critical errors will).


