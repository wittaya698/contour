"""The console: the one layer allowed dependencies (ADR 0019, decision 4).

Everything here runs under the console environment, above `contour` and never
inside Blender. It reads state by importing `lib/`'s Blender-free half and acts
by spawning `./contour`, so *what a mark is* has one definition and this layer
never links against what it launches.
"""
