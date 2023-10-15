from tkinter import messagebox, ttk
import tkinter as tk
import asyncio
import httpx
import re
import os

icon_path = "src/neko-sama.ico"

def on_submit():
    global url, is_vostfr, is_vf
    url = url_entry.get()
    
    if url.startswith("https://neko-sama.fr/"):
        url = url.replace("https://neko-sama.fr/", "https://www.neko-sama.fr/")
    elif url.startswith("www.neko-sama.fr/"):
        url = "https://" + url
    elif url.startswith("neko-sama.fr/"):
        url = "https://www." + url
    elif url.startswith("https://animecat.net/"):
        pass # Aucune modification n'est nécessaire pour ce domaine
    elif not url.startswith("https://www.neko-sama.fr/") and not url.startswith("https://animecat.net/"):
        messagebox.showerror("Erreur", "L'URL doit commencer par 'https://www.neko-sama.fr/' ou 'https://animecat.net/'")
        return


    # Ajout pour gérer les liens /info/
    if "/anime/info/" in url:
        is_vostfr, is_vf = "_vostfr" in url, "_vf" in url
        url = url.replace("/anime/info/", "/anime/episode/")
        url = re.sub(r"_vostfr|_vf", "", url)
        url += "-01_vostfr" if is_vostfr else "-01_vf"

    episode_num_match = re.search(r"-(\d+)_", url)
    if not episode_num_match or not episode_num_match.group(1).isdigit():
        messagebox.showerror("Erreur", "Impossible de trouver le numéro de l'épisode dans l'URL spécifiée")
        return

    is_vostfr, is_vf = "_vostfr" in url, "_vf" in url
    if is_vostfr:
        url = re.sub(r"-(\d+)_vostfr", "-01_vostfr", url)
    elif is_vf:
        url = re.sub(r"-(\d+)_vf", "-01_vf", url)
    else:
        messagebox.showerror("Erreur", "Le lien doit être en VF ou VOSTFR.")
        return

    asyncio.run(main())


async def fetch_episode_link(http_client, episode_num, url):
    next_url = url.replace("01_vostfr" if is_vostfr else "01_vf", "{:02d}_vostfr" if is_vostfr else "{:02d}_vf").format(episode_num)
    response = await http_client.get(next_url)
    if response.status_code == 404:
        return None
    match = re.search(r"(fusevideo.net|fusevideo.io|pstream.net)/e/(\w+)", response.text)
    if match:
        return "Episode {} : https://{}/e/{}\n\n".format(episode_num, match.group(1), match.group(2))
    
def extract_anime_name(url):
    match = re.search(r"/\w+-(.+?)(_vostfr|_vf)", url)
    if match:
        anime_name = match.group(1).replace("-01_", "").replace("-01", "").rstrip('-')
        suffix = match.group(2)

        if suffix == "_vostfr":
            anime_name += "-vostfr"
        elif suffix == "_vf":
            anime_name += "-vf"

        return anime_name.capitalize()

    return None

def save_missing_episodes(anime_name, missing_episodes):
    if not missing_episodes:
        return 

    missing_episodes_file_path = os.path.join("anime_links", anime_name, "missing_episodes.txt")
    with open(missing_episodes_file_path, "w") as f:
        f.write("Episodes manquants:\n")
        for episode_num in missing_episodes:
            f.write(f"Episode {episode_num}\n")


async def main():
    async with httpx.AsyncClient() as http_client:
        episode_num = 1
        links = []
        concurrent_requests = 20

        while True:
            tasks = [fetch_episode_link(http_client, episode_num + i, url) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)

            found_new_links = False
            for result in results:
                if result is None:
                    continue
                found_new_links = True
                links.append(result)
                episode_num += 1

            if not found_new_links:
                break

        anime_name = extract_anime_name(url)
        if anime_name is None:
            messagebox.showerror("Erreur", "Impossible d'extraire le nom de l'anime à partir de l'URL")
            return

        anime_folder_path = os.path.join("anime_links", anime_name)
        os.makedirs(anime_folder_path, exist_ok=True)

        links_file_path = os.path.join(anime_folder_path, "links.txt")

        # Trier les liens par numéro d'épisode
        links.sort(key=lambda link: int(re.search(r"Episode (\d+)", link).group(1)))

        # Supprimer les liens en double
        links = list(set(links))
        links.sort(key=lambda link: int(re.search(r"Episode (\d+)", link).group(1)))

        # Afficher les liens dans la zone de texte
        display_links(links)

        # Écrivez les liens dans le fichier links.txt
        with open(links_file_path, "w") as f:
            f.writelines(links)

        # Collectez et enregistrez les épisodes manquants
        episode_numbers = [int(re.search(r"Episode (\d+)", link).group(1)) for link in links]
        all_episode_numbers = list(range(1, max(episode_numbers) + 1))
        missing_episodes = list(set(all_episode_numbers) - set(episode_numbers))
        save_missing_episodes(anime_name, missing_episodes)

        messagebox.showinfo("Succès", f"Les liens ont été enregistrés dans le dossier '{anime_name}'")

def display_links(links):
    url_text.delete(1.0, tk.END)
    last_episode = 0
    missing_episodes = []

    for link in links:
        url_text.insert(tk.END, link)
        current_episode = int(re.search(r"Episode (\d+)", link).group(1))

        if current_episode != last_episode + 1:
            missing_episodes.extend(list(range(last_episode + 1, current_episode)))

        last_episode = current_episode

    if missing_episodes:
        messagebox.showwarning("Attention", f"Il manque les épisodes suivants: {missing_episodes}")    

# [Thx Sukuna]
def clear_entry():
    url_entry.delete(0, tk.END)
    url_text.delete(1.0, tk.END)

current_mode = "dark"

    
def apply_dark_theme():
    window.configure(background="#333333")
    url_label.configure(fg="#FFFFFF", bg="#333333")
    url_entry.configure(style="Dark.TEntry")
    submit_button.configure(bg="#FFFFFF", fg="#333333")
    clear_button.configure(bg="#FFFFFF", fg="#333333")
    url_text.configure(bg="#222222", fg="#FFFFFF", insertbackground="#FFFFFF")
 
 
# Créez la fenêtre principale
window = tk.Tk()
window.title("Nekoxtract")
window.iconbitmap(default=icon_path)
window.resizable(0, 0)
window.configure(background="#F5F5F5")

# Créez les widgets
url_label = tk.Label(window, text="Entrez l'URL de départ :", font=("Helvetica", 14), fg="#333333", bg="#F5F5F5")
url_label.grid(row=0, column=0, padx=5, pady=5)

url_entry = ttk.Entry(window, width=30, font=("Helvetica", 14))
url_entry.grid(row=0, column=1, padx=5, pady=5)

# [Thx Sukuna]
submit_button = tk.Button(window, text="Extraire les liens", font=("Helvetica", 14), bg="#333333", fg="#FFFFFF", command=on_submit)
submit_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

clear_button = tk.Button(window, text="Clear", font=("Helvetica", 14), bg="#333333", fg="#FFFFFF", command=clear_entry)
clear_button.grid(row=1, column=1, padx=(50,5), pady=5)

url_text = tk.Text(window, width=50, height=20, font=("Helvetica", 14))
url_text.grid(row=2, column=0, columnspan=2, padx=5, pady=5)



def show_info():
    tk.messagebox.showinfo("Infos", "Version: 1.3\nContact: Showzur#0001")

info_button = tk.Button(window, text="i", font=("Helvetica", 14), fg="#333333", bg="#F5F5F5", bd=0, command=show_info)
info_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

info_button = tk.Button(window, text="i", font=("Helvetica", 14), fg="#333333", bg="#F5F5F5", bd=0, command=show_info)
info_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

if current_mode == "dark":
    apply_dark_theme()
    
window.mainloop() 