Scripts in here are for storage_handler_stack.script_create_volume

These scripts create the storage_volume, one at a time, needed for this Storage to work.

These scripts must be intelligent enough to see what volumes already exist, and add the correct remaining volumes.

It shouldnt be called if no volumes are needed, so this check can be left out.

