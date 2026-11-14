# Product Specification — Forge 100K

## Product goal
A searchable web library for original 3D character archetypes and assets, with procedural variations, interactive preview and export.

## User workflows
1. Browse or search a category.
2. Select an archetype and inspect its 3D preview.
3. Configure outfit, body form and palette.
4. Save a preset locally or export a GLB.
5. Upload a GLB to inspect it in the viewport.

## Catalogue model
A catalogue entry is a deterministic tuple: base archetype + style family + body form + palette + variant seed. The current prototype creates virtual entries on demand; it does not claim that each entry is a separately authored production model.

## Production requirements
- Asset registry with stable IDs, metadata, tags, provenance and licence evidence.
- Object storage/CDN for model binaries and textures.
- Background generation pipeline and job status.
- User authentication, collections and upload moderation.
- GLB validation, checksums, download retries and telemetry.
- Rigging, animation, LOD and PBR quality gates before marking assets game-ready.

## Legal requirements
Only original, commissioned or explicitly licensed assets may be distributed. Game franchises may be used as broad genre references only; do not copy proprietary characters, skins, logos, meshes, textures or animations.
