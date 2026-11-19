# Forge 100K Motion & Simulation Lab

## Purpose
A browser-based procedural preview workspace for validating the first animation interaction loop before importing authored production rigs or motion-capture clips.

## Included
- Procedural humanoid preview rig with articulated pelvis, spine, chest, head, arms, elbows, thighs and knees.
- Six deterministic preview clips: idle, walk, run, jump, combat guard and wave interaction.
- Play/pause, restart, timeline scrubbing, playback speed, loop/once/ping-pong modes.
- Solid, wireframe and skeleton-overlay inspection modes.
- Gravity-adjustable ballistic jump trajectory with root-height telemetry.
- FPS/frame/time/root-height telemetry.
- JSON export of the selected clip and simulation parameters.
- Responsive layout and navigation from the main character library.

## Important limits
This is an initial procedural rig and animation-preview system. It is not a production skeleton export, retargeting system, motion-capture dataset, cloth solver, IK/FK authoring tool, facial rig, or collision-certified animation library. The JSON export records clip metadata and parameters; it does not contain baked keyframes or a GLB animation track.

## Run
Serve the repository root over HTTP (for example, `python -m http.server 8000`) and open `/motion-lab.html`. Three.js is loaded from jsDelivr, so network access is required.
