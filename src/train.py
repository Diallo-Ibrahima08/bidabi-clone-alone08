"""
Pipeline d'entraînement - Version 3.0
Modèle : ResNet-18
Catégories : sugar, milk, bread
"""

import os
import csv
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms, models
from PIL import Image

# -------------------------
# Config
# -------------------------
DATA_DIR = "data/raw/images"
CSV_DIR = "data/raw"
MODEL_DIR = "models"
CATEGORIES = ["sugar", "milk", "bread"]
EPOCHS = 10
BATCH_SIZE = 8
LR = 0.001
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15

os.makedirs(MODEL_DIR, exist_ok=True)

# -------------------------
# Dataset
# -------------------------
class FoodDataset(Dataset):
    def __init__(self, data_dir, categories, transform=None):
        self.samples = []
        self.transform = transform
        self.label_map = {cat: i for i, cat in enumerate(categories)}

        for cat in categories:
            img_dir = os.path.join(data_dir, cat)
            if not os.path.exists(img_dir):
                print(f"⚠ Dossier manquant : {img_dir}")
                continue
            for fname in os.listdir(img_dir):
                if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.samples.append((os.path.join(img_dir, fname), self.label_map[cat]))

        print(f"Dataset : {len(self.samples)} images trouvées")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (64, 64), color=(128, 128, 128))
        if self.transform:
            img = self.transform(img)
        return img, label


# -------------------------
# Transforms
# -------------------------
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])


# -------------------------
# Entraînement
# -------------------------
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device : {device}")

    # Dataset complet
    full_dataset = FoodDataset(DATA_DIR, CATEGORIES, transform=train_transform)

    if len(full_dataset) == 0:
        print("❌ Aucune image trouvée. Vérifie data/raw/images/")
        return

    # Split train / val / test
    n = len(full_dataset)
    n_test = max(1, int(n * TEST_SPLIT))
    n_val = max(1, int(n * VAL_SPLIT))
    n_train = n - n_val - n_test

    train_set, val_set, test_set = random_split(full_dataset, [n_train, n_val, n_test])
    print(f"Split → train: {n_train} | val: {n_val} | test: {n_test}")

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE)

    # Modèle ResNet-18
    model = models.resnet18(weights="IMAGENET1K_V1")
    model.fc = nn.Linear(model.fc.in_features, len(CATEGORIES))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    best_val_acc = 0.0
    metrics_log = []

    print("\n--- Début de l'entraînement ---")
    for epoch in range(EPOCHS):
        # Train
        model.train()
        train_loss, train_correct = 0.0, 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * imgs.size(0)
            train_correct += (outputs.argmax(1) == labels).sum().item()

        scheduler.step()

        # Validation
        model.eval()
        val_loss, val_correct = 0.0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * imgs.size(0)
                val_correct += (outputs.argmax(1) == labels).sum().item()

        train_acc = train_correct / n_train
        val_acc = val_correct / n_val

        print(f"Epoch [{epoch+1:02d}/{EPOCHS}] "
              f"Train Loss: {train_loss/n_train:.4f} Acc: {train_acc:.2%} | "
              f"Val Loss: {val_loss/n_val:.4f} Acc: {val_acc:.2%}")

        metrics_log.append([epoch+1, round(train_loss/n_train, 4), round(train_acc, 4),
                             round(val_loss/n_val, 4), round(val_acc, 4)])

        # Sauvegarder le meilleur modèle
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), f"{MODEL_DIR}/best_model.pth")
            print(f"  ✔ Meilleur modèle sauvegardé (val_acc={val_acc:.2%})")

    # Sauvegarder les métriques
    with open(f"{MODEL_DIR}/metrics.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train_loss", "train_acc", "val_loss", "val_acc"])
        writer.writerows(metrics_log)

    print(f"\n✅ Entraînement terminé ! Meilleure val_acc : {best_val_acc:.2%}")
    print(f"   Modèle sauvegardé : {MODEL_DIR}/best_model.pth")
    print(f"   Métriques : {MODEL_DIR}/metrics.csv")


if __name__ == "__main__":
    train()