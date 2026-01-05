# Projet_Accident_BDD
Projet BDD sur les accidents de la route.

Apres avoir copié le lien dans le vscode : 
`git@github.com:zazouu9/Projet_Accident_BDD.git`

il faut s'autentifier : 

### Ajouter une clé SSH
Dans un terminal : 
`ssh-keygen -t ed25519 -C "zazouu9@github.com"`
`cat ~/.ssh/id_ed25519.pub` --> copier le contenue

Dans web git : 
profil > settings > SSHkeys > ajouter une clé --> coller le contenue

`git push -u origin main`


### Ajouter des fichiers sur le git 
1) verifier l'etat du git
`git status`

2) ajouter ou supprimer des fichiers : 
`git add/rm [fichiers]`

3) enregister les fichiers avec un message
`git commit -m "message"`

4) envoyer au repo distant
`git push`


### Recuperer des fichiers sur le git 
1) recuperer des fichiers : 
`git pull`

2) voir les branche 
`git brach `

3) creer une branche
`git branch [nom]`

4) aller sur la branche 
`git checkout [nom]`

5) recuperer les infos de main dans la branche au fur et a mesure
`git rebase`