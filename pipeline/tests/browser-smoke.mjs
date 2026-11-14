import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

const base = process.env.FORGE_BASE_URL || "http://127.0.0.1:4173";
const browser = await chromium.launch({headless:true,args:["--no-sandbox","--use-gl=angle","--use-angle=swiftshader","--enable-webgl","--ignore-gpu-blocklist"]});
const page = await browser.newPage({acceptDownloads:true});
const errors=[];
page.on("pageerror",e=>errors.push(e.message));
try {
  await page.goto(base,{waitUntil:"networkidle",timeout:60000});
  await page.locator("#view canvas").waitFor({state:"visible",timeout:30000});
  await page.waitForFunction(()=>!document.querySelector("#previewTitle")?.textContent.includes("Loading preview"));
  if (!(await page.locator("#cards .asset").count())) throw new Error("Character catalogue did not render");
  await page.locator("#apply").click();
  await page.locator("#outfit").selectOption("Armored");
  await page.locator("#apply").click();
  const downloadPromise=page.waitForEvent("download",{timeout:30000});
  await page.locator("#download").click();
  const download=await downloadPromise;
  const target=path.join(os.tmpdir(),download.suggestedFilename());
  await download.saveAs(target);
  const bytes=await fs.readFile(target);
  if (bytes.length<20 || bytes.subarray(0,4).toString("ascii")!=="glTF") throw new Error("GLB export did not produce a valid GLB header");
  await page.locator("#file").setInputFiles(target);
  await page.getByText("GLB loaded",{exact:true}).waitFor({timeout:30000});
  if(errors.length) throw new Error("Browser errors: "+errors.join(" | "));
  console.log(JSON.stringify({status:"pass",canvas:true,catalogue:true,glbBytes:bytes.length,glbMagic:bytes.subarray(0,4).toString("ascii"),uploadPreview:true}));
  await fs.rm(target,{force:true});
} finally {
  await browser.close();
}
