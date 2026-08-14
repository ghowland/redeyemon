"""
shared

Shared Resources

by Geoff Howland <geoff AT ge01f DOT com>


Shared resources consists of:

- Shared Locks: to ensure resource control can be limited, and confirm resources
    are being used.  State is never saved for process restarts.  Locks are lost.

- Shared Counters: to track values of interest to different threads, updated
    in an atomic fashion.  Usable as unique ID incrementors and thread safe.
    State can be saved for process restart, snapshotting only.

- Shared State: to track data in buckets in a thread-safe manner.  Shared
    state allows disperate threads to use each other's information, safely.
    State can be saved for process restart, archival method and snapshotting
    is available.

- Message Queues: inter-thread communication or delayed processing.  Thread
    safe and can be stored to disk for restart survival.  Storage methods
    include archive and snapshotting, and can be tuned.

- Thread Safe Dictionary: used as a core part of all thread-safe operations,
    the ThreadSafeDict is a core tool for ensuring multiple threads can access
    common information in a thread-safe manner.

- Thread Safe List: used as a core part of all thread-safe operations,
    the ThreadSafeList is a core tool for ensuring multiple threads can access
    common information in a thread-safe manner.

- Logging: A best-of-breed logging solution for single hosts or a large
    distributed system.  Made for ease of use, and maximum information control,
    will store locally, rotate, send to syslog, keep collection information to
    be scraped for central storage, keep track of the scripts and line numbers
    being logged from, and many other useful and configurable parameters.
    Defaults should "just work".  Can target to different logging tracks, going
    into different files, or whatever.
    
    Logging has less to do with shared resources than these other items, but
    I have found all programs need robust logging, and the standard Python
    logging library is great in lots of ways, but takes a lot of effort to set
    up, and more effort to do distributed things correctly, and much more effort
    to do scalable distributed things, so I'm just doing a version that will
    be universably available and work easily and scale massively, and including
    it with the rest of the shared resources to make it a more useful library.
    
    Feel free to ignore any parts of this library you wish.  :)


The purpose of this shared set of libraries is to wrap the most common functions
needed for a small piece of code to operate on an enterprise level.

Small code using this library can take advantage of the benefits that
distributed systems technologies provide to keep logic small, and pass the
responsibility of labor to other small code blocks, so testing can be better,
and complexity can be reduced.  More of the complexity can be handed to the
well-tested shared resource code, which provides the framework for smaller
code to operate robustly and provide a breadth of features.

This is not sales-speak, several tiny scripts should be able to pull off very
large and complex seeming jobs if they use the shared resources properly, and
should be able to scale to thousands of nodes communicating and sharing data, if
required, while still keeping custom code small and easy to change and verify.

These libraries are built with the intend of being used in operating-system
level scripts.  If you are trying to do high transactions with minimal memory
footprints, you will want to use a specific storage solution for that purpose,
like a stand-alone Message Queue service (ex. ActiveMQ), or a State Server
(ex. reddis).

These libraries are intendend to make development easier and
faster, but are not meant to take the place of specialized fine-tuned services
if scale and performance is required.
"""


import sharedlock
import sharedcounter
import sharedstate

import messagequeue

import threadsafedict
import threadsafelist


#TODO(g): Create a generic shared connection pool, which can create a pool
#   of any shared connection, and create multiple kinds of pools, such as
#   'write' and 'read' pools.
#
#   This is something that is done over and over, and often poorly.  Do it well!
#
#   This is non-sharded, for the simplest case.  Sharding adds on more
#     configuration, and can extend this.
#
#   Allow this to be made as intermediary "connection pool load balancer", so
#     that systems with a lot of connection requirements, but limited listeners
#     can funnel requests to a system with a lot of open requests, and make
#     it's connections that way.  Can use "sessions" like cursors, to allow
#     multiple transactions before giving up the connection session, and
#     returning it to the pool.  Or timeout.  Other pool-reclamation available.
#import connectionpool

#TODO(g): An enhancement to connectionpool, this deals with sharding and
#   can do data and access sharding, by a given sharding strategy (runs of
#   shards, by different ID ranges, etc).
#import connectionpool_sharded

#TODO(g): A collection of all the state, for every node.  So that nodes can
#   share their states, and each is kept in a node-descriptor bucket, so that
#   only the node can update it's state.  Then we know when the node's state
#   was last updated, and can regionally collect state, and have access to
#   any nodes state, from any other node, by accessing the regional collector.
#   N-levels of depth are needed, not just "regions", which will allow any
#   constructed system to be able to scale and efficiently pass and segment
#   data sets, so each system is manageable.
#
#   Adding a "reduce" function to this, could allow statistical analysis of all
#   node states, and create a way to look for different sorts of data anamolies
#   and trends.
#
#import nodestate

#TODO(g): Create a distributed state system, that works off of a single
#   node state, but uses a quorum (mix of locks and updates) to create a shared
#   state, which can be shared among N nodes, with regional relays specified).
#   This way large distributed systems can share state, using the CAP and quorum
#   methodology for ensuring the best state wins.
#
#   Also is a perfect way to pass around peer-to-peer real time game state.
#
#import distributedstate

# Storage: Data survives process restarts.
#TODO(g): These will be integrated, as any desired statefulness requires both
#   an archive log, and a snapshot.  Recovery will happen automatically on
#   initialization of data with the snapshot (when created, state is restorted
#   as the state file-pattern is specified, and so the latest snapshot will be
#   loaded and archives after that will be replayed until it is up to date).
#
#   Performance is traded for correctness.  Ease-of-use is the highest goal,
#   so these benefits are delivered "for free" on proper use of the system.
#
#   Write-behind can be specified for archival information, so high speed
#   systems can be developed, but the default is atomic archiving on change.
#
#   Snapshotting can be done on time, number of archive entries, or some other
#   algorithm.  Use procblocks to make it very easy to change.
#import archive
#import snapshot

# Logging
#
#TODO(g): Logging.  I want a top-notch, all batteries included logging system
#    that deals with syslog/syslogng, always has targets (default=''), always describes
#    what script and what line, and a mini-stack (if asked for), and has a
#    definition file (procblock?!?) to describe where targets go, and how to
#    rotate and deal with them, and can be created from Motherbrain service
#    details.  Especially for remote logging, and logging concentration.
#    
#    This needs to be a distributed systems logging wrapper, that handles easy
#    script logging on a single developer machine with no-effort, but scales
#    to running on many thousands of nodes in different regions with their own
#    collectors, aggregators, and searchers.
#    
#    Needs to be able to quickly look at recent history, so time series
#    integration will be required, so that triggers can be put on logs for
#    processing and inclusion in reactive scripting.
import log

# Stack based information, required for detailed logging.
import stack

# Merge with stack?  Or log?  Could be a full module inside our shared logging
#   to provide a ton of good error and stack information in automated logging.
import error_info

# Work with dicts and sequences via strings: "var.-1.(var2).var3"
import dotinspect
