# Stage 2: CLIP embeddings, prompt-based photo quality, zero-shot scene tags. Usage: python3 -I clipscore.py <scratch>
import sys, os, json, torch, open_clip, numpy as np
from PIL import Image
S = sys.argv[1]
torch.set_num_threads(4)
model, _, pre = open_clip.create_model_and_transforms("ViT-L-14", pretrained="openai")
tok = open_clip.get_tokenizer("ViT-L-14"); model.eval()

POS = ["a professional award-winning sports photojournalism photo, sharp focus, decisive moment",
       "a compelling newspaper photograph with clear subject and strong composition",
       "a sharp, well-composed event photo with expressive faces and emotion"]
NEG = ["a blurry out of focus snapshot", "a boring amateur photo with no clear subject",
       "a motion-blurred, badly framed photo", "a photo of people's backs with nothing happening"]
SCENES = {"soccer": "a soccer match on a rainy field", "basketball": "a basketball game in an indoor gym",
          "badminton": "a badminton match in a gym", "baseball": "a baseball game on a baseball field",
          "esports": "students playing a video game tournament on computers in an esports arena",
          "band": "a rock band performing on a concert stage", "dance": "a dance team performing on stage",
          "hiphop": "a rapper performing hip hop on stage with a microphone",
          "cheer": "a cheerleading squad performing on stage", "ceremony": "an award ceremony on stage with trophies",
          "rccar": "small autonomous RC cars racing on a track", "presentation": "a person giving a presentation in an auditorium",
          "coding": "students coding on laptops at a hackathon", "crowd": "a crowd of spectators cheering",
          "booth": "people at an event booth or registration desk"}

with torch.no_grad():
    def txt(ts):
        e = model.encode_text(tok(ts)); return e / e.norm(dim=-1, keepdim=True)
    tp, tn, ts = txt(POS), txt(NEG), txt(list(SCENES.values()))
    names = sorted(x[:-4] for x in os.listdir(f"{S}/thumbs") if x.endswith(".jpg"))
    embs, out = [], []
    B = 16
    for i in range(0, len(names), B):
        chunk = names[i:i+B]
        x = torch.stack([pre(Image.open(f"{S}/thumbs/{n}.jpg").convert("RGB")) for n in chunk])
        e = model.encode_image(x); e = e / e.norm(dim=-1, keepdim=True)
        q = (100 * e @ torch.cat([tp, tn]).T).softmax(-1)
        qual = q[:, :len(POS)].sum(-1)
        sc = (100 * e @ ts.T).softmax(-1)
        keys = list(SCENES)
        for j, n in enumerate(chunk):
            top = sc[j].topk(2)
            out.append({"name": n, "clipq": float(qual[j]), "scene": keys[top.indices[0]],
                        "scene_p": float(top.values[0]), "scene2": keys[top.indices[1]]})
        embs.append(e.numpy())
        print(i, flush=True)
    np.save(f"{S}/emb.npy", np.concatenate(embs)); json.dump(out, open(f"{S}/clip.json", "w"))
