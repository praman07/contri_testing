# Runtime Architecture

The runtime coordinates lifecycle, modules, dependency injection, providers, events, health, and recovery.

## Startup

Startup loads configuration, initializes logging, creates the service container, registers core interfaces, starts the event bus, discovers modules, validates dependencies, initializes modules in dependency order, starts providers, restores context and memory, and enters running state.

## Shutdown

Shutdown stops incoming actions, cancels active plans safely, flushes memory, publishes shutdown events, stops providers, stops modules in reverse order, persists recoverable state, and exits cleanly.

## Dependency injection

All subsystems consume interfaces, not concrete implementations. Providers and model clients are replaceable.

## Modules

Modules declare identity, dependencies, lifecycle hooks, subscribed events, published events, health checks, and owned interfaces.

## Events

Events carry facts and state transitions. They are immutable once published and include correlation IDs for multi-step tasks.

## Recovery and health

The runtime tracks heartbeats, failed providers, failed plans, memory errors, event backlog, and degraded capabilities. Recovery must prefer safe pause over uncontrolled continuation.
