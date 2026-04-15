# Otimizando-Rota-de-Drones
O objetivo é desenvolver um agente que planeje a rota mais eficiente para um único drone que deve ir de um ponto de partida a um destino em uma área urbana simulada.

A "eficiência" da rota não é apenas a distância, mas uma combinação de tempo de voo e consumo de energia. O ambiente possui as seguintes características:

· Mapa 3D: A cidade é representada por um grid tridimensional (células (x, y, z)), onde cada célula pode ter características específicas.

· Vento: Existem variações de vento em diferentes altitudes e locais. Voar contra o vento ou em áreas de forte turbulência aumenta o consumo de energia e/ou diminui a velocidade (aumenta o tempo).

· Zonas de Restrição Temporárias: Certas áreas do espaço aéreo podem se tornar temporariamente restritas devido a eventos, obras ou questões de segurança (ex: "No-Fly Zones" dinâmicas). O drone deve desviar dessas zonas enquanto estiverem ativas.
