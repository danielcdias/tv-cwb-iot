# tv-cwb-iot

Projeto de pesquisa **Terraço Verde Curitiba IoT**. Rede de sensores criada para monitorar protótipo de telhado verde, efetuando comparação entre tipo de cobertura intensiva e extensiva. Coleta de dados sobre temperatura do solo, quantidade de chuva, atraso de pico e água absorvida.

Este projeto implementa o firmware dos microcontroladores ligados aos sensores, o border router que liga a rede de sensores à internet, e do servidor de aplicação que recebe dos dados coletados, os trata e dispobibiliza através de aplicação web e móvel.

As pastas do projeto estão organizadas da seguinte forma:
- *contiki*: sistema operacional contiki, contendo o código para criação do firmware dos microcontroladores responsáveis pela leitura dos sensores.
- *docker*: configuração para executar o servidor de aplicação (Django/Python) e o banco de dados (MariaDB) em um docker composer.
- *forwarder*: aplicação em Python responsável por receber os dados dos microcontroladores e encaminhá-los ao servidor de aplicação.
- *mobile*: aplicação móvel desenvolvida em Google Flutter para apresentar os dados lidos dos sensores (ainda não implementado).
- *pcb*: projeto de placas impressas utilizadas no projeto.
- *server*: servidor de aplicação desenvolvido em Django/Python, responsável por receber, tratar, armazenar e apresentar os dados lidos pela rede de sensores.
