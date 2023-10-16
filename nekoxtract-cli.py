# Importation des modules nécessaires
import os
import re
import asyncio
import httpx

# Vérification de l'existence du fichier "links.txt" et suppression s'il existe déjà
if os.path.exists("links.txt"):
    os.remove("links.txt")

# Demande de l'URL de départ à l'utilisateur
url = input("Entrez l'URL de départ : ")

# Vérification que l'URL commence bien par "https://animecat.net/" ou "https://www.neko-sama.fr/" ou "https://neko-sama.fr/"
if not url.startswith("https://animecat.net/") and not url.startswith("https://www.neko-sama.fr/") and not url.startswith("https://neko-sama.fr/"):
    print("L'URL doit commencer par 'https://animecat.net/' ou 'https://www.neko-sama.fr/' ou 'https://neko-sama.fr/'")
    exit()


# Ajout pour gérer les liens /info/
if "/anime/info/" in url:
    # Vérification si l'URL est en VF ou VOSTFR
    is_vostfr, is_vf = "_vostfr" in url, "_vf" in url
    # Remplacement de "/anime/info/" par "/anime/episode/"
    url = url.replace("/anime/info/", "/anime/episode/")
    # Suppression de "_vostfr" ou "_vf" dans l'URL
    url = re.sub(r"_vostfr|_vf", "", url)
    # Ajout du numéro de l'épisode et de la langue
    url += "-01_vostfr" if is_vostfr else "-01_vf"

# Recherche du numéro de l'épisode dans l'URL
episode_num_match = re.search(r"-(\d+)_", url)
if not episode_num_match or not episode_num_match.group(1).isdigit():
    print("Impossible de trouver le numéro de l'épisode dans l'URL spécifiée")
    exit()

# Vérification si l'URL se termine par "_vf" ou "_vostfr"
if not url.endswith("_vf") and not url.endswith("_vostfr"):
    print("Le lien doit se terminer par '_vf' ou '_vostfr'.")
    exit()

# Remplacement du numéro de l'épisode par "01" dans l'URL
if is_vostfr:
    url = re.sub(r"-(\d+)_vostfr", "-01_vostfr", url)
elif is_vf:
    url = re.sub(r"-(\d+)_vf", "-01_vf", url)
else:
    print("Le lien doit être en VF ou VOSTFR.")
    exit()
    

# Fonction pour récupérer le nom et le donner au dossier
def extract_anime_name(url):
    # Utilisez des expressions régulières pour extraire le nom de l'anime à partir de l'URL
    match = re.search(r"/(\d+)-(.+?)_(vostfr|vf)", url)
    if match:
        anime_name = match.group(2).replace("-", " ").capitalize()
        # Exclure "01" du nom de l'anime
        anime_name = anime_name.replace(" 01", "").replace("01", "")
        suffix = match.group(3)

        if suffix == "vostfr":
            anime_name += " VOSTFR"
        elif suffix == "vf":
            anime_name += " VF"

        return anime_name

    return None

   
    
# Fonction pour récupérer le lien de l'épisode
async def fetch_episode_link(http_client, episode_num, url):
    # Génération de l'URL de l'épisode en fonction de l'épisode en cours de récupération
    next_url = url.replace("01_vostfr" if is_vostfr else "01_vf", "{:02d}_vostfr" if is_vostfr else "{:02d}_vf").format(episode_num)
    # Récupération de la page de l'épisode
    response = await http_client.get(next_url)
    # Vérification si la page de l'épisode existe
    if response.status_code == 404:
        return None
    # Recherche du lien de l'épisode dans le code HTML de la page de l'épisode
    match = re.search(r"(fusevideo.net|fusevideo.io|pstream.net)/e/(\w+)", response.text)
    if match:
        # Retour du lien de l'épisode
        return "Episode {} : https://{}/e/{}\n\n".format(episode_num, match.group(1), match.group(2))


def save_missing_episodes(anime_name, missing_episodes):
    if not missing_episodes:
        return

    missing_episodes_file_path = os.path.join("anime_links", anime_name, "missing_episodes.txt")
    with open(missing_episodes_file_path, "w") as f:
        f.write("Episodes manquants:\n")
        for episode_num in missing_episodes:
            f.write(f"Episode {episode_num}\n")


# Fonction principale
async def main():
    # Création du client HTTP
    async with httpx.AsyncClient() as http_client:
        # Initialisation du numéro de l'épisode à 1
        episode_num = 1
        # Initialisation de la liste des liens
        links = []

        # Modifier cette valeur pour contrôler le nombre de requêtes simultanées
        concurrent_requests = 20

        while True:
            # Création des tâches pour récupérer les liens des épisodes
            tasks = [fetch_episode_link(http_client, episode_num + i, url) for i in range(concurrent_requests)]
            # Récupération des résultats de toutes les tâches
            results = await asyncio.gather(*tasks)

            # Vérification si de nouveaux liens ont été trouvés
            found_new_links = False
            for result in results:
                if result is None:
                    continue
                found_new_links = True
                links.append(result)
                episode_num += 1

            # Sortie de la boucle si aucun nouveau lien n'a été trouvé
            if not found_new_links:
                break

        # Si aucune lien n'a été trouvé, n'effectuez aucune opération supplémentaire
        if not links:
            print("Aucun lien n'a été trouvé.")
            return

        # Créez un dossier avec le nom de l'anime
        anime_name = extract_anime_name(url)
        if anime_name is not None:
            anime_folder_path = os.path.join("anime_links", anime_name)
            os.makedirs(anime_folder_path, exist_ok=True)

            # Écrivez les liens dans un fichier "links.txt" à l'intérieur du dossier de l'anime
            links_file_path = os.path.join(anime_folder_path, "links.txt")
            with open(links_file_path, "w") as f:
                f.writelines(links)
 
        # Collectez et enregistrez les épisodes manquants
        episode_numbers = [int(re.search(r"Episode (\d+)", link).group(1)) for link in links]
        all_episode_numbers = list(range(1, max(episode_numbers) + 1))
        missing_episodes = list(set(all_episode_numbers) - set(episode_numbers))
        save_missing_episodes(anime_name, missing_episodes)

        # Vérifie s'il y a des épisodes manquants et imprime un message si c'est le cas
        if missing_episodes:
            print(f"Il manque les épisodes suivants : {missing_episodes}")
            print(f"Les liens manquants ont été enregistrés dans le fichier 'missing_episodes.txt'")
            print(f"les liens ont bien été enregistrées dans le dossier {anime_name}")
        else:
            print(f"Tous les épisodes ont été récupérés avec succès")
            print(f"les liens ont bien été enregistrées dans le dossier {anime_name}")

# Lancement de la fonction principale
asyncio.run(main()) 