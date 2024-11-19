import argparse
import csv
import sys
import networkx as nx

# Variabile globale per gestire lo stato dello Split Horizon
SPLIT_HORIZON = False

def parse_arguments():
    """
    Analizza gli argomenti della linea di comando e restituisce i parametri forniti dall'utente.
    """
    parser = argparse.ArgumentParser(description='Simulazione del protocollo Distance Vector Routing')
    parser.add_argument('-f', '--file', required=True, help='File CSV contenente la topologia della rete')
    return parser.parse_args()

def read_csv(file_path):
    """
    Legge il file CSV specificato e restituisce una lista di nodi e archi.

    Args:
        file_path (str): Percorso del file CSV.

    Returns:
        tuple: Una tupla contenente la lista dei nodi e la lista degli archi.
    """
    nodes = []
    edges = []
    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            data = [row for row in reader if row and not row[0].startswith("#")]
            if data:
                nodes = data[0]
                for edge in data[1:]:
                    if len(edge) == 3:
                        u, v, weight = edge
                        try:
                            weight = float(weight)
                            edges.append((u, v, {'weight': weight}))
                        except ValueError:
                            print(f"Attenzione: Peso non valido '{weight}' per l'arco {u}-{v}.")
                    else:
                        print(f"Attenzione: Formato non valido per l'arco: {edge}.")
            else:
                print("Errore: Il file CSV è vuoto o non contiene dati validi.")
                sys.exit(1)
    except FileNotFoundError:
        print(f"Errore: File '{file_path}' non trovato.")
        sys.exit(1)
    except Exception as e:
        print(f"Errore nella lettura del file '{file_path}': {e}")
        sys.exit(1)
    return nodes, edges

class RoutingTable:
    """
    Rappresenta la tabella di routing per un nodo nella rete.

    Attributes:
        node (str): Nome del nodo.
        table (dict): Dizionario con le rotte verso gli altri nodi.
    """

    def __init__(self, node, graph):
        self.node = node
        self.graph = graph
        self.table = {}
        self.initialize_table()

    def initialize_table(self):
        """
        Inizializza la tabella di routing impostando i costi diretti e infiniti.
        """
        for dest in self.graph.nodes:
            if dest == self.node:
                self.table[dest] = (0, '-')
            elif dest in self.graph.neighbors(self.node):
                cost = self.graph.edges[self.node, dest]['weight']
                self.table[dest] = (cost, dest)
            else:
                self.table[dest] = (float('inf'), None)

    def update_shortest_path(self, dest, cost, next_hop):
        """
        Aggiorna la rotta verso una destinazione specifica.

        Args:
            dest (str): Nodo di destinazione.
            cost (float): Costo per raggiungere la destinazione.
            next_hop (str): Prossimo nodo lungo il percorso.
        """
        self.table[dest] = (cost, next_hop)

def display_routing_table(node, graph):
    """
    Mostra la tabella di routing per un nodo specifico.

    Args:
        node (str): Nome del nodo.
        graph (networkx.Graph): Grafo della rete.
    """
    table = graph.nodes[node]['routing_table'].table
    print(f"\nTabella di Routing per {node}:")
    print("{:<15} {:<10} {:<15}".format("Destinazione", "Costo", "Prossimo Nodo"))
    for dest, (cost, next_hop) in sorted(table.items()):
        cost_str = "∞" if cost == float('inf') else cost
        next_hop_str = '-' if next_hop is None else next_hop
        print("{:<15} {:<10} {:<15}".format(dest, cost_str, next_hop_str))
    print()

def validate_graph(graph):
    """
    Verifica se il grafo contiene archi con peso negativo.

    Args:
        graph (networkx.Graph): Grafo della rete.

    Raises:
        SystemExit: Se viene rilevato un arco con peso negativo.
    """
    for u, v, data in graph.edges(data=True):
        if data.get('weight', 0) < 0:
            print(f"Errore: Arco con peso negativo tra {u} e {v}.")
            sys.exit(1)

def bellman_ford_iteration(graph):
    """
    Esegue un'iterazione dell'algoritmo di Bellman-Ford per aggiornare le tabelle di routing.

    Args:
        graph (networkx.Graph): Grafo della rete.

    Returns:
        bool: True se ci sono stati aggiornamenti, False altrimenti.
    """
    updated = False
    for node in graph.nodes:
        routing_table = graph.nodes[node]['routing_table']
        for neighbor in graph.neighbors(node):
            neighbor_table = graph.nodes[neighbor]['routing_table']
            cost_to_neighbor = graph.edges[node, neighbor]['weight']
            for dest in graph.nodes:
                if dest == node:
                    continue
                neighbor_cost, _ = neighbor_table.table.get(dest, (float('inf'), None))
                if SPLIT_HORIZON and neighbor_table.table.get(dest, (float('inf'), None))[1] == node:
                    continue  # Applicazione dello Split Horizon
                new_cost = cost_to_neighbor + neighbor_cost
                current_cost, _ = routing_table.table.get(dest, (float('inf'), None))
                if new_cost < current_cost:
                    routing_table.update_shortest_path(dest, new_cost, neighbor)
                    updated = True
    return updated

def check_stability(graph):
    """
    Controlla se le tabelle di routing sono stabili.

    Args:
        graph (networkx.Graph): Grafo della rete.

    Returns:
        bool: True se stabili, False altrimenti.
    """
    return not bellman_ford_iteration(graph)

def process_command(command, args, graph):
    """
    Esegue il comando inserito dall'utente.

    Args:
        command (str): Comando inserito.
        args (list): Argomenti del comando.
        graph (networkx.Graph): Grafo della rete.
    """
    if command == 'help':
        print_help()
    elif command == 'show-table':
        if not args:
            print("Errore: Specificare almeno un nodo o 'all'.")
            return
        if 'all' in args:
            for node in graph.nodes:
                display_routing_table(node, graph)
        else:
            for node in args:
                if node in graph.nodes:
                    display_routing_table(node, graph)
                else:
                    print(f"Errore: Nodo {node} non trovato.")
    elif command == 'shortest-path':
        if len(args) != 2:
            print("Errore: Il comando 'shortest-path' richiede due nodi.")
            return
        src, dest = args
        if src in graph.nodes and dest in graph.nodes:
            try:
                path = nx.shortest_path(graph, src, dest, weight='weight')
                cost = nx.shortest_path_length(graph, src, dest, weight='weight')
                print(f"Percorso da {src} a {dest}: {' -> '.join(path)} (Costo: {cost})")
            except nx.NetworkXNoPath:
                print(f"Errore: Nessun percorso tra {src} e {dest}.")
        else:
            print("Errore: Uno o entrambi i nodi non esistono.")
    elif command == 'update-tables':
        if not args:
            print("Errore: Specificare un numero di iterazioni o 'stable'.")
            return
        if args[0] == 'stable':
            iterations = 0
            while True:
                iterations += 1
                if not bellman_ford_iteration(graph):
                    print(f"Le tabelle di routing sono stabili dopo {iterations} iterazioni.")
                    break
        else:
            try:
                iterations = int(args[0])
                for _ in range(iterations):
                    bellman_ford_iteration(graph)
                print(f"Eseguite {iterations} iterazioni di scambio.")
            except ValueError:
                print("Errore: L'argomento deve essere un numero intero o 'stable'.")
    elif command == 'toggle-split-horizon':
        global SPLIT_HORIZON
        SPLIT_HORIZON = not SPLIT_HORIZON
        stato = 'attivato' if SPLIT_HORIZON else 'disattivato'
        print(f"Split Horizon {stato}.")
    else:
        print(f"Comando '{command}' non riconosciuto. Digitare 'help' per la lista dei comandi.")

def print_help():
    """
    Stampa l'elenco dei comandi disponibili.
    """
    help_text = """
    Comandi disponibili:
        help                                Mostra questo messaggio di aiuto.
        show-table <nodo>/all               Mostra la tabella di routing del nodo specificato o di tutti i nodi.
        shortest-path <nodo1> <nodo2>       Mostra il percorso più breve tra due nodi.
        update-tables <n>/stable            Esegue n iterazioni o fino alla stabilità delle tabelle di routing.
        toggle-split-horizon                Attiva/disattiva lo Split Horizon.
        exit                                Esce dal programma.
    """
    print(help_text)

def main():
    """
    Funzione principale che gestisce l'esecuzione della simulazione.
    """
    args = parse_arguments()
    nodes, edges = read_csv(args.file)

    # Creazione del grafo della rete
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    # Validazione del grafo
    validate_graph(graph)

    # Inizializzazione delle tabelle di routing
    for node in graph.nodes:
        graph.nodes[node]['routing_table'] = RoutingTable(node, graph)

    print("Simulazione del protocollo Distance Vector Routing")
    print("Digitare 'help' per la lista dei comandi.")

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            parts = user_input.split()
            command = parts[0].lower()
            cmd_args = parts[1:]
            if command in ['exit', 'quit']:
                print("Uscita dal programma.")
                break
            else:
                process_command(command, cmd_args, graph)
        except KeyboardInterrupt:
            print("\nInterruzione dalla tastiera. Uscita dal programma.")
            break

if __name__ == "__main__":
    main()