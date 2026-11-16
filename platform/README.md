# Desert Sentinel — platform (Explore + Newsletter)

Next.js prototype for the NASA Space Apps **Desert Sentinel** product surface.

## Run

```bash
cd platform
npm install
npm run dev
```

Dev server defaults to port **3847**.

## Routes

- `/` → redirects to `/explore`
- `/explore` — map, actions, rankings, carbon financial impact
- `/learn-by-playing` — interactive 3D WebXR field mission about SAR evidence, desertification, partnerships, and restoration
- `/newsletter` — stakeholder newsletter signup

The immersive mode on `/learn-by-playing` uses native WebXR and requires a compatible browser/headset plus a secure origin (HTTPS, or `localhost` during development).

Palette: **CLIMA / Terra e luz** (Café · Barro · Sol · Ocre · Mel).
