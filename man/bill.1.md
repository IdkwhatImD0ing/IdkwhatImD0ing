```text
BILL(1)                    User Commands                    BILL(1)
```

## NAME

**bill** — AI-first builder; converts caffeine and deadline pressure into shipped demos

## SYNOPSIS

**bill** [**--ship**] [**--demo**] [**--voice**] [_project_]...
**bill** **--hackathon** [**--hours** _24_] [**--sleep** _0_]

## DESCRIPTION

**bill** leads 日月神教, the Sun Moon Divine Sect (the [README](../README.md)
this page belongs to). In a previous life he was a userland process
resident on tianni (ART3M1S OS, Rev 5080), since 2021; the machine is now
the sect's formation. Accepts underspecified ideas on stdin and emits
working demos on stdout, typically within one weekend. Known to bind to
any available voice-AI API at runtime.

Invoked without arguments, **bill** defaults to `--ship`.

## OPTIONS

**--ship**
: Default mode. Optimizes for demo-ready over perfect. See _thehackathonplaybook.dev_ for the theory.

**--demo**
: Loud mode. Output includes a live audience.

**--voice**
: Attaches an ElevenLabs pipeline to whatever the current project is. This flag is frequently implied.

**--hackathon**
: Competitive mode. Historical exit data: 35 wins across 58 invocations (60%).

**--sleep**
: Recognized for POSIX compliance. Not implemented.

## EXIT STATUS

**0**  shipped
**1**  shipped anyway
**>1** never observed in production

## BUGS

Sleeps occasionally (upstream wontfix: a stele for sleep was commissioned
in the Stele Forest and never carved).

Spontaneously starts new projects while existing projects are still
compiling. Marked WONTFIX; several maintainers consider it the core
feature.

## SEE ALSO

**art3m1s.me**(443), **hackathons.log**(5), **.plan**(7), the [README](../README.md) this page escaped from.

```text
SUN MOON DIVINE SECT         2026-10-24                     BILL(1)
```
