'''
Description: 古诗词生成模型
Author: rainym00d, Ethan00Si
Github: https://github.com/rainym00d, https://github.com/Ethan00Si
Date: 2021-05-07 13:10:00
LastEditors: rainym00d
LastEditTime: 2021-05-09 13:08:08
'''
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils import data
import numpy as np
import os


class PoetryModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim):
        '''
        ***********请在此写入你的代码**********
        定义模型：
        1. 定义模型隐藏层维度, hidden_dim为读入的隐藏层维度
        2. 使用词嵌入表示(word embedding), embedding_dim为读入的嵌入向量的维度
        3. 定义LSTM模型（推荐使用2层LSTM）
        4. 定义线性模型（从 hidden_dim 映射到 vocab_size）
        '''
        super().__init__()
        dim = embedding_dim
        self.embedding_dim= dim
        self.hidden_dim=hidden_dim#定义模型隐藏层的维度
        self.embeddings=nn.Embedding(vocab_size,self.embedding_dim)#定义词嵌入表示：读入的次维度；输出的词嵌入向量维度
        self.rnn=nn.LSTM(self.embedding_dim,self.hidden_dim,2)#定义LSTM模型；使用两层LSTM
        self.output=nn.Linear(self.hidden_dim,vocab_size)#古诗生成case中，每个字即为一类，所以分类数为vocab_size

    def forward(self, input, hidden=None):
        '''
        *********请在此处输入你的代码*********
        输入：input, 它的size是(sequence_length, batch_size)
        输出（返回值）：output(预测值)，hidden(隐藏层的值)
            * output的size是(sequence_length, batch_size, vocab_size)
            * hidden的size是(4, batch_size, hidden_size)
                * h_0 (2, batch_size, hidden_size)
                * c_0 (2, batch_size, hidden_size)
        定义模型函数：
            * 判断输入的参数是否有hidden，没有的话新建一个全0的tensor
            * 将input进行词向量嵌入
            * 使用lstm模型
            * 用线性层将output映射到vocab_size的维度上
            * 返回output, hidden
        '''

        # 以下是2层LSTM所需要的状态初始化(包括h_0和c_0)代码
        seq_len, batch_size = input.size()#seq_len:序列长度【诗/诗句长度】；batch_size：分批操作，并行运算的诗/诗句数量
        if hidden is None:
            h_0 = input.data.new(2, batch_size, self.hidden_dim).fill_(0).float()
            c_0 = input.data.new(2, batch_size, self.hidden_dim).fill_(0).float()
        else:
            h_0, c_0 = hidden
        # 请在下面补充forward函数的其它代码
        input_embeddings=self.embeddings(input)#对输入的input进行词向量嵌入
        hiddens, hidden=self.rnn(input_embeddings, (h_0, c_0))#自动接收上一轮的隐藏值h
        output=self.output(hiddens)

        return  output, hidden


class Model():
    def __init__(self, vocab_size, embedding_dim, hidden_dim):
        """
        创建模型和优化器，初始化线性模型和优化器超参数
        * 参数
            * learning_rate
            * epoches
            * model_save_path: 模型保存路径
            * device: cuda or cpu
        * 模型
            * 创建PoetryModel的实例, 命名为model
            * 定义optimizer
            * 定义loss function
        """
        self.lr = 1e-3  # 学习率
        self.epoches = 100  # 训练epoch数量
        self.model_save_path = './model/PoetryModel'  # 模型保存路径
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # 指定训练的device，优先使用GPU，GPU不可用时加载CPU

        self.model = PoetryModel(vocab_size, embedding_dim, hidden_dim).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        self.loss_function = nn.CrossEntropyLoss()

    def _save_model(self, epoch):
        """
        保存模型，用于训练时保存指定epoch的模型
        """
        print('[INFO] Saving to %s_%s.pth' % (self.model_save_path, epoch))
        torch.save(self.model.state_dict(), '%s_%s.pth' % (self.model_save_path, epoch))

    def _load_model(self, epoch):
        """
        加载模型，用于加载指定epoch的模型。
        目前代码中没有用到。
        可以在训练到一半但中断了之后，自行修改代码，从最近的epoch加载，然后继续训练，以节省时间。
        或者训练完毕后，下次再跑程序，就直接加载模型，省去训练时间。
        """
        print('[INFO] Loading from %s_%s.pth' % (self.model_save_path, epoch))
        self.model.load_state_dict(torch.load('%s_%s.pth' % (self.model_save_path, epoch), map_location=self.device))

    def train(self, dataloader):
        """
        训练函数
        """
        # 开始训练
        for epoch in range(self.epoches):
            loss_list = []
            for ii, data_ in enumerate(dataloader):
                print('epoch {}: batch {}'.format(epoch, ii), end='\r')
                # 训练
                data_ = data_.long().transpose(1, 0).contiguous().to(self.device)
                self.optimizer.zero_grad()
                input_, target = data_[:-1, :], data_[1:, :]
                output, _ = self.model(input_)
                # permute(0,2,1)是为了让output从(seq_len, batch_size, vocab_size)变成(seq_len, vocab_size, batch_size)
                # 与 target的(seq_len, batch_size)对应
                output = output.permute(0, 2, 1)
                loss = self.loss_function(output, target)
                loss.backward()
                self.optimizer.step()

                loss_list.append(loss.item())

            epoch_loss = sum(loss_list) / len(loss_list)#啥意思？【截至目前epoch的平均loss值吧】
            print("[INFO] loss of epoch %s: %s" % (epoch, epoch_loss))

            # 保存模型参数
            if epoch % 10 == 0:#每10轮保存一回model参数
                self._save_model(epoch)

    def test(self, start_words, ix2word, word2ix, max_gen_len=200):
        """
        description: 给定几个词，根据这几个词接着生成一首完整的诗歌
        example:
            start_words：u'深度学习'
            生成：
            深度学习书不怪，今朝月下不胜悲。
            芒砀月殿春光晓，宋玉堂中夜月升。
            玉徽美，玉股洁。心似镜，澈圆珠，金炉烟额红芙蕖。
        提示:
            一个字一个字的生成诗歌
            将start_words一个字一个字的作为input输入模型
            第一次输入模型时，hidden为None，之后hidden都是上次的返回结果
            当生成的字为'<EOP>'诗歌结束生成
        """
        test_input=torch.tensor([word2ix[char] for char in start_words])
        hidden=None
        output,hidden=self.model(test_input)
        poem=[]
        poem.append(start_words)
        for i in range(max_gen_len):
            output,hidden=self.model(hidden)
            poem.append(ix2word[output])
            if ix2word[output]=='<EOP>':
                break
        print(poem)





    def acrostic_test(self, start_words, ix2word, word2ix, max_gen_len=200):
        """
        descrption: 生成藏头诗
        example:
            start_words : u'深度学习'
            生成：
            深宫新月明，皎皎明月明。
            度风飘飖飏，照景澄清明。
            学化不可夺，低心不可怜。
            习人不顾盼，仰面空踟蹰。
        提示:
            与上一个函数类似，但需要特殊处理一下“藏头”
            一句结束，即生成“。”或“!”时，诗歌的下一个字为读入的“藏头”。
            此时模型的读入为“藏头”对应的字，其他情况下模型读入的是上次生成的字。
            当所有“藏头”都生成了一句诗，诗歌生成完毕。
        """
        test_input = torch.tensor([word2ix[char] for char in start_words])
        hidden = None
        poem = []
        while len(poem)<= max_gen_len:
            for word_vector in test_input:
                output, hiddens = self.model(word_vector)
                poem.append(ix2word[output])
                while ix2word[output] != '。'and ix2word[output] != '！':
                    output,hidden =self.model(hidden)
                    poem.append(ix2word[output])
        print(poem)


def load_data(data_path):
    """
    return word2ix: dict,每个字对应的序号，形如u'月'->100
    return ix2word: dict,每个序号对应的字，形如'100'->u'月'
    return poet_data: numpy数组，每一行是一首诗对应的字的下标
    """
    if os.path.isfile(data_path):
        data = np.load(data_path, allow_pickle=True)
        poet_data, word2ix, ix2word = data['data'], data['word2ix'].item(), data['ix2word'].item()

        return word2ix, ix2word, poet_data
    else:
        print('[ERROR] Data File Not Exists')
        exit()


def decode_poetry(idx, word2ix, ix2word, poet_data):
    """
    解码诗歌数据
    输入:
        idx: 第几首诗歌(共311823首，idx in [0, 311822])
    """
    assert (idx < poet_data.shape[0] and idx >= 0)

    row = poet_data[idx]

    results = ''.join([
        ix2word[char] if ix2word[char] != '</s>' and ix2word[char] != '<EOP>'
                         and ix2word[char] != '<START>' else ''
        for char in row
    ])
    return results


def main():
    # 获取数据
    data_path = './data/Poetry_data_word2ix_ix2word.npz'
    word2ix, ix2word, poet_data = load_data(data_path)

    # 测试诗词解码
    idx = 1000
    poetry = decode_poetry(idx, word2ix, ix2word, poet_data)
    print('poetry id: %d\ncontent: %s' % (idx, poetry))

    # 转换为tensor与dataloader
    poet_data = poet_data[:1000, ]  # 为测试方便，只截取了前1000条数据训练。后续代码跑通了并且可以用GPU时，可以用全部数据
    poet_data = torch.from_numpy(poet_data)
    dataloader = data.DataLoader(poet_data,
                                 batch_size=128,
                                 shuffle=True)

    # 定义模型
    model = Model(len(word2ix), 128, 256)

    # 查看目前使用的是GPU or CPU
    print('[INFO] Device Is %s' % model.device)

    # 模型训练
    model.train(dataloader)

    # 测试生成藏头诗
    start_words = "深度学习"
    result = model.acrostic_test(start_words, ix2word, word2ix)
    print(''.join(result))

    # 测试普通生成诗词
    start_words = "深度学习"
    result = model.test(start_words, ix2word, word2ix)
    print(''.join(result))




if __name__ == "__main__":
    main()

