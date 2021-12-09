# Most code from https://github.com/aladdinpersson/Machine-Learning-Collection/blob/master/ML/Projects/text_generation_babynames/generating_names.py

import torch
import torch.nn as nn
import string
import random
import unidecode
from collections import defaultdict

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

all_characters = string.ascii_lowercase + ' \n'
n_characters = len(all_characters)

# file = unidecode.unidecode(open("data/names.txt").read())
file = unidecode.unidecode(open("data/data.txt").read())

def default_value():
    return 0

class RNN(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super(RNN, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.embed = nn.Embedding(input_size, hidden_size)
        self.lstm = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x, hidden, cell):
        out = self.embed(x)
        out, (hidden, cell) = self.lstm(out.unsqueeze(1), (hidden, cell))
        out = self.fc(out.reshape(out.shape[0], -1))
        return out, (hidden, cell)

    def init_hidden(self, batch_size):
        hidden = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(device)
        cell = torch.zeros(self.num_layers, batch_size, self.hidden_size).to(device)
        return hidden, cell


class Generator:
    def __init__(self):
        self.chunk_len = 250
        self.num_epochs = 5000
        self.batch_size = 1
        self.print_every = 50
        self.hidden_size = 256
        self.num_layers = 2
        self.lr = 0.003
        self.rnn = RNN(n_characters, self.hidden_size, self.num_layers, n_characters).to(device)

    def load_model(self, path):
        self.rnn.load_state_dict(torch.load(path))

    def char_tensor(self, string):
        tensor = torch.zeros(len(string)).long()
        for c in range(len(string)):
            tensor[c] = all_characters.index(string[c])
        return tensor

    def get_random_batch(self):
        start_idx = random.randint(0, len(file) - self.chunk_len)
        end_idx = start_idx + self.chunk_len + 1
        text_str = file[start_idx:end_idx]
        text_input = torch.zeros(self.batch_size, self.chunk_len)
        text_target = torch.zeros(self.batch_size, self.chunk_len)

        for i in range(self.batch_size):
            text_input[i, :] = self.char_tensor(text_str[:-1])
            text_target[i, :] = self.char_tensor(text_str[1:])

        return text_input.long(), text_target.long()

    def generate(self, predict_len=100, initial_str="a", temperature=0.85):
        hidden, cell = self.rnn.init_hidden(batch_size=self.batch_size)
        initial_input = self.char_tensor(initial_str)
        predicted = initial_str

        for p in range(len(initial_str) - 1):
            _, (hidden, cell) = self.rnn(
                initial_input[p].view(1).to(device), hidden, cell
            )

        last_char = initial_input[-1]

        for p in range(predict_len):
            output, (hidden, cell) = self.rnn(
                last_char.view(1).to(device), hidden, cell
            )
            output_dist = output.data.view(-1).div(temperature).exp()
            top_char = torch.multinomial(output_dist, 1)[0]
            predicted_char = all_characters[top_char]
            predicted += predicted_char
            last_char = self.char_tensor(predicted_char)

        return predicted

    def complete_string(self, initial_string, temperature=0.85):
        hidden, cell = self.rnn.init_hidden(batch_size=self.batch_size)
        initial_input = self.char_tensor(initial_string)
        predicted = initial_string

        for p in range(len(initial_string) - 1):
            _, (hidden, cell) = self.rnn(
                initial_input[p].view(1).to(device), hidden, cell
            )

        last_char = initial_input[-1]
        predicted_char = ''

        while predicted_char != '\n':
            output, (hidden, cell) = self.rnn(
                last_char.view(1).to(device), hidden, cell
            )
            output_dist = output.data.view(-1).div(temperature).exp()
            top_char = torch.multinomial(output_dist, 1)[0]
            predicted_char = all_characters[top_char]
            predicted += predicted_char
            last_char = self.char_tensor(predicted_char)

            if predicted_char == '\n':
                return predicted

        return predicted

    def estimate_prob_dist(self, initial_string, n=1000, temperature=0.85):
        samples = defaultdict(default_value)
        for _ in range(n):
            sample = self.complete_string(initial_string,
                    temperature=temperature)
            samples[sample] += 1
        return samples

    def random_prediction(self, temperature=0.85):
        possible_preps = ['a', 'ab', 'abante', 'ad', 'apud', 'con', 'contra', 'coram',
        'cum', 'de', 'e', 'ex', 'extra', 'in', 'inter', 'iuxta',
         'ob', 'palam', 'per', 'post', 'prae', 'pro', 'propter',
        'sine', 'sub', 'super', 'trans']

        prep = random.choice(possible_preps) + ' '

        return self.complete_string(prep, temperature=temperature)

    # input_size, hidden_size, num_layers, output_size
    def train(self):

        optimizer = torch.optim.Adam(self.rnn.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss()
        # writer = SummaryWriter(f"runs/names0")  # for tensorboard

        print("=> Starting training")

        for epoch in range(1, self.num_epochs + 1):
            inp, target = self.get_random_batch()
            hidden, cell = self.rnn.init_hidden(batch_size=self.batch_size)

            self.rnn.zero_grad()
            loss = 0
            inp = inp.to(device)
            target = target.to(device)

            for c in range(self.chunk_len):
                output, (hidden, cell) = self.rnn(inp[:, c], hidden, cell)
                loss += criterion(output, target[:, c])

            loss.backward()
            optimizer.step()
            loss = loss.item() / self.chunk_len

            if epoch % self.print_every == 0:
                print('')
                print(f"Epoch: {epoch}")
                print(f"{(epoch / self.num_epochs) * 100}% trained")
                print(f"Loss: {loss}")
                print(self.generate())

        torch.save(self.rnn.state_dict(), 'case_predictor.pt')

if __name__ == '__main__':
    gennames = Generator()
    gennames.train()

# print('')
# print(gennames.generate('in insul'))
# print('')
# print(gennames.generate('ab insul'))
# print('')
# print(gennames.generate('de insul'))
# print('')
# print(gennames.generate('in memori'))
# print('')
# print(gennames.generate('a memori'))
# print('')
# print(gennames.generate('de memori'))
# print('')
# print(gennames.complete_string('de memori'))
